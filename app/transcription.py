from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from .config import settings


class TranscriptionError(RuntimeError):
    pass


_model: WhisperModel | None = None
_model_lock = threading.Lock()


def _model_instance() -> WhisperModel:
    """Create the Whisper model once and reuse it for later requests."""
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            try:
                _model = WhisperModel(
                    settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                    download_root=settings.whisper_model_dir,
                    cpu_threads=settings.whisper_cpu_threads,
                    num_workers=settings.whisper_num_workers,
                )
            except Exception as exc:
                raise TranscriptionError(
                    f"Unable to load Whisper model '{settings.whisper_model}': {exc}"
                ) from exc

    return _model


def _language_arg(language: str | None) -> str | None:
    value = (language or "").strip().lower()
    return None if value in {"", "auto", "detect"} else value


def _transcribe_one(
    chunk: Path,
    *,
    language: str,
    timestamps: bool,
) -> tuple[str, list[dict[str, Any]], str | None]:
    model = _model_instance()
    language_value = _language_arg(language)

    try:
        segments, info = model.transcribe(
            str(chunk),
            language=language_value,
            beam_size=settings.whisper_beam_size,
            vad_filter=settings.whisper_vad_filter,
            word_timestamps=False,
        )

        text_parts: list[str] = []
        result_segments: list[dict[str, Any]] = []
        for segment in segments:
            text = (segment.text or "").strip()
            if text:
                text_parts.append(text)
            if timestamps:
                result_segments.append(
                    {
                        "start": round(float(segment.start), 3),
                        "end": round(float(segment.end), 3),
                        "text": text,
                    }
                )

        detected_language = getattr(info, "language", None)
        return " ".join(text_parts).strip(), result_segments, detected_language
    except Exception as exc:
        raise TranscriptionError(f"Local Whisper transcription failed: {exc}") from exc


async def transcribe_chunks(
    chunks: list[Path],
    *,
    language: str = "auto",
    timestamps: bool = False,
) -> tuple[str, list[dict[str, Any]], str | None]:
    """Transcribe chunks locally without blocking the ASGI event loop."""
    all_text: list[str] = []
    all_segments: list[dict[str, Any]] = []
    detected_language: str | None = None

    for index, chunk in enumerate(chunks):
        text, segments, chunk_language = await asyncio.to_thread(
            _transcribe_one,
            chunk,
            language=language,
            timestamps=timestamps,
        )

        if text:
            all_text.append(text)
        if detected_language is None and chunk_language:
            detected_language = chunk_language

        if timestamps:
            offset = index * settings.chunk_seconds
            for segment in segments:
                all_segments.append(
                    {
                        "start": round(float(segment["start"]) + offset, 3),
                        "end": round(float(segment["end"]) + offset, 3),
                        "text": segment["text"],
                    }
                )

    return "\n".join(all_text).strip(), all_segments, detected_language
