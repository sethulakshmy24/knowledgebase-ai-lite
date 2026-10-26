
import re
from collections.abc import Awaitable, Callable

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"
CHUNK_SIZE = 6000

ProgressCallback = Callable[[int, int, str], Awaitable[None]]


def split_into_chunks(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
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


async def ask_ollama(
    client: httpx.AsyncClient,
    prompt: str,
    max_tokens: int = 1200,
) -> str:
    response = await client.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
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
    return await ask_ollama(client, prompt, max_tokens=1200)


async def summarize_text_async(
    text: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    if not text or len(text.strip()) < 20:
        raise ValueError("Please provide more content to summarize.")

    chunks = split_into_chunks(text)
    notes: list[str] = []

    timeout = httpx.Timeout(300.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for index, chunk in enumerate(chunks, start=1):
            note = await summarize_chunk(
                client, chunk, index, len(chunks)
            )
            notes.append(note)

            if on_progress:
                await on_progress(index, len(chunks), note)

        # Reduce notes in groups so the final prompt stays manageable.
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
                    await ask_ollama(client, prompt, max_tokens=1600)
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

        return await ask_ollama(client, final_prompt, max_tokens=3000)


# Preserve compatibility with existing synchronous callers for now.
def summarize_text(text: str) -> str:
    import asyncio

    return asyncio.run(summarize_text_async(text))
