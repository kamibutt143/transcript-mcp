from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .media import download_audio, split_audio
from .transcription import transcribe_chunks
from .validation import validate_facebook_url


async def transcribe_facebook(
    url: str,
    *,
    language: str = "auto",
    timestamps: bool = False,
) -> dict[str, Any]:
    normalized_url = validate_facebook_url(url)

    with tempfile.TemporaryDirectory(prefix="softnest-transcript-") as temp_dir:
        workdir = Path(temp_dir)
        media = await download_audio(normalized_url, workdir)
        chunks = await split_audio(media.audio_path, workdir)
        transcript, segments, detected_language = await transcribe_chunks(
            chunks,
            language=language,
            timestamps=timestamps,
        )

        return {
            "success": True,
            "source": "facebook",
            "source_url": media.webpage_url or normalized_url,
            "title": media.title,
            "duration_seconds": media.duration_seconds,
            "language": detected_language or language,
            "requested_language": language,
            "transcription_engine": "faster-whisper",
            "timestamps": timestamps,
            "transcript": transcript,
            "segments": segments if timestamps else [],
            "chunk_count": len(chunks),
            "extractor": media.extractor,
        }
