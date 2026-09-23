from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import settings


class MediaError(RuntimeError):
    pass


@dataclass
class MediaResult:
    audio_path: Path
    title: str | None
    duration_seconds: float | None
    webpage_url: str | None
    extractor: str | None


async def _run(*args: str, timeout: int | None = None) -> tuple[str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except TimeoutError:
        process.kill()
        await process.communicate()
        raise MediaError(f"Command timed out: {args[0]}")

    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")
    if process.returncode != 0:
        tail = err.strip()[-2500:]
        raise MediaError(f"{args[0]} failed: {tail or 'unknown error'}")
    return out, err


async def download_audio(url: str, workdir: Path) -> MediaResult:
    workdir.mkdir(parents=True, exist_ok=True)
    output_template = str(workdir / "source.%(ext)s")

    command = [
        "yt-dlp",
        "--no-playlist",
        "--no-progress",
        "--no-warnings",
        "--print-json",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--postprocessor-args",
        "ffmpeg:-ac 1 -ar 16000 -b:a 32k",
        "--output",
        output_template,
    ]

    if settings.ytdlp_cookies_file:
        command.extend(["--cookies", settings.ytdlp_cookies_file])

    command.append(url)

    stdout, _ = await _run(
        *command,
        timeout=settings.download_timeout_seconds,
    )

    metadata: dict[str, Any] = {}
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            metadata = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    audio_path = workdir / "source.mp3"
    if not audio_path.exists():
        candidates = sorted(workdir.glob("source.*"))
        if not candidates:
            raise MediaError("yt-dlp completed but no audio file was produced")
        audio_path = candidates[0]

    duration_raw = metadata.get("duration")
    duration = float(duration_raw) if isinstance(duration_raw, (int, float)) else None
    if duration is None:
        probe_out, _ = await _run(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
            timeout=30,
        )
        try:
            duration = float(probe_out.strip())
        except ValueError:
            duration = None

    if duration and duration > settings.max_video_seconds:
        raise MediaError(
            f"Video is too long ({duration:.0f}s). Maximum is {settings.max_video_seconds}s"
        )

    return MediaResult(
        audio_path=audio_path,
        title=metadata.get("title"),
        duration_seconds=duration,
        webpage_url=metadata.get("webpage_url") or url,
        extractor=metadata.get("extractor_key") or metadata.get("extractor"),
    )


async def split_audio(audio_path: Path, workdir: Path) -> list[Path]:
    chunks_dir = workdir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(chunks_dir / "chunk-%04d.mp3")

    await _run(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        str(settings.chunk_seconds),
        "-reset_timestamps",
        "1",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "32k",
        pattern,
        timeout=settings.download_timeout_seconds,
    )

    chunks = sorted(chunks_dir.glob("chunk-*.mp3"))
    if not chunks:
        raise MediaError("Unable to split extracted audio")
    return chunks
