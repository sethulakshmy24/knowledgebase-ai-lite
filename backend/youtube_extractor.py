
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    video_id = ""

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith("/embed/"):
            video_id = parsed.path.split("/")[2]
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/")[2]
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Please provide a valid YouTube video URL.")

    return video_id


def extract_youtube_transcript(url: str) -> str:
    video_id = extract_video_id(url)

    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(
            snippet.text for snippet in transcript
        ).strip()
    except Exception as exc:
        raise ValueError(
            "Transcript unavailable for this video. Try another video or paste its transcript."
        ) from exc

    if len(text) < 20:
        raise ValueError("The video transcript is too short to summarize.")

    return text[:300000]
