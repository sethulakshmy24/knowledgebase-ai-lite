
import json
import os
import re
from collections.abc import Awaitable, Callable

import httpx
from dotenv import load_dotenv

load_dotenv()

# Provider configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

CHUNK_SIZE = 6000

ProgressCallback = Callable[[int, int, str], Awaitable[None]]
TextCallback = Callable[[str], Awaitable[None]]


def validate_provider() -> None:
    if AI_PROVIDER not in {"ollama", "openrouter"}:
        raise ValueError(
            f"Unsupported AI_PROVIDER: {AI_PROVIDER}. "
            "Choose 'ollama' or 'openrouter'."
        )

    if AI_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. "
            "Add it to backend/.env or your deployment environment."
        )


def split_into_chunks(
    text: str,
    max_chars: int = CHUNK_SIZE,
) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            chunks.extend(
                sentence[start:start + max_chars]
                for start in range(0, len(sentence), max_chars)
            )
            continue

        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks


# ---------------------------
# Ollama: non-streaming
# ---------------------------

async def ask_ollama_local(
    client: httpx.AsyncClient,
    prompt: str,
    max_tokens: int = 1200,
) -> str:
    response = await client.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
                "num_predict": max_tokens,
            },
        },
    )
    response.raise_for_status()

    result = response.json().get("response", "").strip()

    if not result:
        raise RuntimeError("Ollama returned an empty response.")

    return result


# ---------------------------
# Ollama: streaming
# ---------------------------

async def ask_ollama_local_stream(
    client: httpx.AsyncClient,
    prompt: str,
    on_text: TextCallback,
    max_tokens: int = 1200,
) -> str:
    full_response = ""
    word_buffer = ""

    async with client.stream(
        "POST",
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
                "num_predict": max_tokens,
            },
        },
    ) as response:
        response.raise_for_status()

        async for line in response.aiter_lines():
            if not line:
                continue

            data = json.loads(line)
            token = data.get("response", "")

            full_response += token
            word_buffer += token

            if len(word_buffer.split()) >= 12:
                await on_text(word_buffer)
                word_buffer = ""

            if data.get("done"):
                break

    if word_buffer:
        await on_text(word_buffer)

    if not full_response.strip():
        raise RuntimeError("Ollama returned an empty response.")

    return full_response


# ---------------------------
# OpenRouter: non-streaming
# ---------------------------


async def ask_openrouter(
    client: httpx.AsyncClient,
    prompt: str,
    max_tokens: int = 3000,
) -> str:
    validate_provider()

    response = await client.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "KnowledgeBase AI Lite",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
             "reasoning": {
                "effort": "minimal",
                "exclude": True
            },
            "stream": False,
        },
    )

    response.raise_for_status()
    data = response.json()

    if data.get("error"):
        raise RuntimeError(
            f"OpenRouter error: {data['error']}"
        )

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(
            f"OpenRouter returned no choices. Response: {data}"
        )

    choice = choices[0]
    message = choice.get("message", {})
    content = message.get("content")

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    if isinstance(content, str) and content.strip():
        return content.strip()

    finish_reason = choice.get("finish_reason", "unknown")
    usage = data.get("usage", {})
    reasoning_tokens = usage.get(
        "completion_tokens_details", {}
    ).get("reasoning_tokens", 0)

    raise RuntimeError(
        "OpenRouter returned no text. "
        f"Model: {data.get('model', OPENROUTER_MODEL)}; "
        f"finish_reason: {finish_reason}; "
        f"reasoning_tokens: {reasoning_tokens}. "
        "Check model availability and token limits."
    )


# ---------------------------
# OpenRouter: streaming
# ---------------------------

async def ask_openrouter_stream(
    client: httpx.AsyncClient,
    prompt: str,
    on_text: TextCallback,
    max_tokens: int = 1200,
) -> str:
    validate_provider()

    full_response = ""
    word_buffer = ""

    async with client.stream(
        "POST",
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "KnowledgeBase AI Lite",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": True,
        },
    ) as response:
        response.raise_for_status()

        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue

            raw_data = line[len("data:"):].strip()

            if raw_data == "[DONE]":
                break

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            choices = data.get("choices", [])
            if not choices:
                continue

            delta = choices[0].get("delta", {})
            token = delta.get("content", "")

            if isinstance(token, list):
                token = "".join(
                    item.get("text", "")
                    for item in token
                    if isinstance(item, dict)
                )

            if not isinstance(token, str) or not token:
                continue

            full_response += token
            word_buffer += token

            # Emit incremental updates approximately every 12 words.
            if len(word_buffer.split()) >= 12:
                await on_text(word_buffer)
                word_buffer = ""

    if word_buffer:
        await on_text(word_buffer)

    if not full_response.strip():
        raise RuntimeError("OpenRouter returned an empty response.")

    return full_response


# ---------------------------
# Provider-independent API
# ---------------------------

async def ask_ai(
    client: httpx.AsyncClient,
    prompt: str,
    max_tokens: int = 1200,
) -> str:
    validate_provider()

    if AI_PROVIDER == "ollama":
        return await ask_ollama_local(client, prompt, max_tokens)

    return await ask_openrouter(client, prompt, max_tokens)


async def ask_ai_stream(
    client: httpx.AsyncClient,
    prompt: str,
    on_text: TextCallback,
    max_tokens: int = 1200,
) -> str:
    validate_provider()

    if AI_PROVIDER == "ollama":
        return await ask_ollama_local_stream(
            client, prompt, on_text, max_tokens
        )

    return await ask_openrouter_stream(
        client, prompt, on_text, max_tokens
    )


# Compatibility aliases for existing callers.
# These now route to whichever provider AI_PROVIDER selects.
async def ask_ollama(
    client: httpx.AsyncClient,
    prompt: str,
    max_tokens: int = 1200,
) -> str:
    return await ask_ai(client, prompt, max_tokens)


async def ask_ollama_stream(
    client: httpx.AsyncClient,
    prompt: str,
    on_text: TextCallback,
    max_tokens: int = 1200,
) -> str:
    return await ask_ai_stream(
        client, prompt, on_text, max_tokens
    )


# ---------------------------
# Summarization
# ---------------------------

async def summarize_chunk(
    client: httpx.AsyncClient,
    chunk: str,
    index: int,
    total: int,
) -> str:
    prompt = f"""
You are an expert technical instructor creating Python learning notes.

Summarize section {index} of {total} from a Python learning transcript.

Requirements:
- Explain concepts in clear, beginner-friendly language.
- Preserve technical details and terminology.
- Include code examples when available and explain what they do.
- Capture definitions, practical tips, and common mistakes.
- Do not invent content not supported by the transcript.
- Use headings and bullet points.
- Avoid a generic two-sentence summary.

TRANSCRIPT SECTION:
{chunk}

Write detailed notes for this section.
"""
    return await ask_ai(client, prompt, max_tokens=1200)


async def summarize_text_async(
    text: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    validate_provider()

    if not text or len(text.strip()) < 20:
        raise ValueError("Please provide more content to summarize.")

    chunks = split_into_chunks(text)
    notes: list[str] = []

    timeout = httpx.Timeout(300.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Summarize each chunk.
        for index, chunk in enumerate(chunks, start=1):
            note = await summarize_chunk(
                client, chunk, index, len(chunks)
            )
            notes.append(note)

            if on_progress:
                await on_progress(index, len(chunks), note)

        # Reduce intermediate notes when there are many chunks.
        while len(notes) > 6:
            reduced: list[str] = []

            for start in range(0, len(notes), 6):
                group = notes[start:start + 6]

                prompt = """
Combine these technical learning notes into coherent notes.
Preserve distinct concepts, definitions, code examples, and tips.
Remove repetition without discarding useful details.

NOTES:
""" + "\n\n".join(group)

                reduced.append(
                    await ask_ai(client, prompt, max_tokens=1600)
                )

            notes = reduced

        final_prompt = """
Create comprehensive, well-organized Python learning notes from
the section notes below.

Include:
1. Topics covered
2. Key concepts and explanations
3. Important syntax and code examples
4. Practical tips and common mistakes
5. Key takeaways

Use Markdown headings and code fences. Preserve distinct topics.
Do not invent content or claim the transcript covered something it did not.
These are study notes, not a short summary.

SECTION NOTES:
""" + "\n\n".join(notes)

        return await ask_ai(
            client, final_prompt, max_tokens=3000
        )


async def stream_final_notes(
    notes: list[str],
    on_text: TextCallback,
) -> str:
    validate_provider()

    prompt = """
Create comprehensive, well-organized Python learning notes from
the section notes below.

Include:
1. Topics covered
2. Key concepts and explanations
3. Important syntax and code examples
4. Practical tips and common mistakes
5. Key takeaways

Use Markdown headings and code fences. Preserve distinct topics.
Do not invent content not supported by the notes.
These are detailed study notes, not a short summary.

SECTION NOTES:
""" + "\n\n".join(notes)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=10.0)
    ) as client:
        return await ask_ai_stream(
            client,
            prompt,
            on_text,
            max_tokens=3000,
        )


# Preserve compatibility with synchronous callers.
def summarize_text(text: str) -> str:
    import asyncio

    return asyncio.run(summarize_text_async(text))
