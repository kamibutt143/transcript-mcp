from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import settings


class TranscriptionError(RuntimeError):
    pass


_client: AsyncOpenAI | None = None


def _client_instance() -> AsyncOpenAI:
    global _client
    if not settings.openai_api_key:
        raise TranscriptionError("OPENAI_API_KEY is not configured")
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def _language_arg(language: str | None) -> str | None:
    value = (language or "").strip().lower()
    return None if value in {"", "auto", "detect"} else value


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"text": str(value)}


async def transcribe_chunks(
    chunks: list[Path],
    *,
    language: str = "auto",
    timestamps: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    client = _client_instance()
    all_text: list[str] = []
    all_segments: list[dict[str, Any]] = []
    language_value = _language_arg(language)

    for index, chunk in enumerate(chunks):
        kwargs: dict[str, Any] = {
            "file": chunk,
            "model": settings.timestamp_model if timestamps else settings.transcript_model,
        }
        if language_value:
            kwargs["language"] = language_value

        if timestamps:
            kwargs["response_format"] = "verbose_json"
            kwargs["timestamp_granularities"] = ["segment"]

        with chunk.open("rb") as fh:
            kwargs["file"] = fh
            response = await client.audio.transcriptions.create(**kwargs)

        payload = _to_dict(response)
        text = (payload.get("text") or "").strip()
        if text:
            all_text.append(text)

        if timestamps:
            offset = index * settings.chunk_seconds
            for segment in payload.get("segments") or []:
                if hasattr(segment, "model_dump"):
                    segment = segment.model_dump()
                if not isinstance(segment, dict):
                    continue
                all_segments.append(
                    {
                        "start": round(float(segment.get("start", 0)) + offset, 3),
                        "end": round(float(segment.get("end", 0)) + offset, 3),
                        "text": str(segment.get("text", "")).strip(),
                    }
                )

    return "\n".join(all_text).strip(), all_segments
