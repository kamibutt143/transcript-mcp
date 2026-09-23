from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    service_api_key: str | None
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    whisper_model_dir: str
    whisper_cpu_threads: int
    whisper_num_workers: int
    whisper_beam_size: int
    whisper_vad_filter: bool
    max_video_seconds: int
    chunk_seconds: int
    download_timeout_seconds: int
    ytdlp_cookies_file: str | None
    mcp_allowed_hosts: list[str]
    mcp_allowed_origins: list[str]
    port: int


def load_settings() -> Settings:
    return Settings(
        service_api_key=os.getenv("SERVICE_API_KEY", "").strip() or None,
        whisper_model=os.getenv("WHISPER_MODEL", "small").strip() or "small",
        whisper_device=os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu",
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8",
        whisper_model_dir=os.getenv("WHISPER_MODEL_DIR", "/models").strip() or "/models",
        whisper_cpu_threads=_int("WHISPER_CPU_THREADS", 0),
        whisper_num_workers=max(1, _int("WHISPER_NUM_WORKERS", 1)),
        whisper_beam_size=max(1, _int("WHISPER_BEAM_SIZE", 5)),
        whisper_vad_filter=_bool("WHISPER_VAD_FILTER", True),
        max_video_seconds=_int("MAX_VIDEO_SECONDS", 10800),
        chunk_seconds=max(60, _int("CHUNK_SECONDS", 1200)),
        download_timeout_seconds=_int("DOWNLOAD_TIMEOUT_SECONDS", 300),
        ytdlp_cookies_file=os.getenv("YTDLP_COOKIES_FILE", "").strip() or None,
        mcp_allowed_hosts=_csv(
            "MCP_ALLOWED_HOSTS",
            "localhost,localhost:*,127.0.0.1,127.0.0.1:*",
        ),
        mcp_allowed_origins=_csv("MCP_ALLOWED_ORIGINS"),
        port=_int("PORT", 8000),
    )


settings = load_settings()
