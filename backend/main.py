
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from summarizer import summarize_text
from article_extractor import extract_article_text
import httpx
from fastapi import HTTPException
from youtube_extractor import extract_youtube_transcript
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from youtube_extractor import extract_youtube_transcript
from summarizer import summarize_text_async, stream_final_notes
import traceback

app = FastAPI(title="KnowledgeBase AI Lite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "KnowledgeBase AI Lite",
    }


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50000)


class SummarizeResponse(BaseModel):
    summary: str


@app.post("/api/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest):
    summary = summarize_text(request.text)
    return SummarizeResponse(summary=summary)


class ArticleRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


@app.post("/api/summarize-url", response_model=SummarizeResponse)
def summarize_url(request: ArticleRequest):
    try:
        article_text = extract_article_text(request.url)
        summary = summarize_text(article_text)
        return SummarizeResponse(summary=summary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve this article. Try pasting its text instead.",
        ) from exc


class YouTubeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


@app.post("/api/summarize-youtube", response_model=SummarizeResponse)
def summarize_youtube(request: YouTubeRequest):
    try:
        transcript = extract_youtube_transcript(request.url)
        summary = summarize_text(transcript)
        return SummarizeResponse(summary=summary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.websocket("/ws/summarize")
async def websocket_summarize(websocket: WebSocket):
    await websocket.accept()

    async def send_event(event: str, **data):
        await websocket.send_json({
            "event": event,
            **data,
        })

    try:
        request = await websocket.receive_json()

        mode = request.get("mode")
        content = request.get("content", "").strip()

        if mode not in {"text", "url", "youtube"}:
            await send_event(
                "error",
                message="Unsupported input mode.",
            )
            return

        if not content:
            await send_event(
                "error",
                message="Please provide text or a URL.",
            )
            return

        if mode == "text":
            source_text = content

        elif mode == "youtube":
            await send_event(
                "progress",
                stage="extracting",
                message="Extracting YouTube transcript...",
            )
            source_text = await run_in_threadpool(
                extract_youtube_transcript,
                content,
            )

        else:
            # Use the existing article extractor without blocking
            # the event loop.
            from article_extractor import extract_article_text

            await send_event(
                "progress",
                stage="extracting",
                message="Extracting article text...",
            )
            source_text = await run_in_threadpool(
                extract_article_text,
                content,
            )

        async def on_chunk_progress(index: int, total: int, note: str):
            await send_event(
                "chunk_completed",
                index=index,
                total=total,
                note=note,
                message=f"Completed section {index} of {total}.",
            )
        async def on_text(text: str):
            await send_event("text_delta", text=text)

        await send_event(
            "progress",
            stage="summarizing",
            message="Generating detailed learning notes...",
        )

        # First summarize the source in chunks.
        section_notes = await summarize_text_async(
            source_text,
            on_progress=on_chunk_progress,
        )

        # Stream the final notes to the frontend in small batches.
        summary = await stream_final_notes(
            [section_notes],
            on_text=on_text,
        )

        await send_event(
            "completed",
            summary=summary,
            message="Summary completed successfully.",
        )

        await send_event(
            "completed",
            summary=summary,
            message="Summary completed.",
        )

    except WebSocketDisconnect:
        # The client disconnected. The request can no longer
        # receive progress or results.
        return

    except Exception as exc:
        traceback.print_exc()  # Print the full error to Render logs

        try:
            await send_event(
                "error",
                message=str(exc) or "Summarization failed.",
            )
        except (WebSocketDisconnect, RuntimeError):
            pass

    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass

async def send_text(text: str):
    await send_event("text_delta", text=text)
