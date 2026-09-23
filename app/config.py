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


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    service_api_key: str | None
    transcript_model: str
    timestamp_model: str
    max_video_seconds: int
    chunk_seconds: int
    download_timeout_seconds: int
    ytdlp_cookies_file: str | None
    mcp_allowed_hosts: list[str]
    mcp_allowed_origins: list[str]
    port: int


def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        service_api_key=os.getenv("SERVICE_API_KEY", "").strip() or None,
        transcript_model=os.getenv("TRANSCRIPT_MODEL", "gpt-transcribe").strip(),
        timestamp_model=os.getenv("TIMESTAMP_MODEL", "whisper-1").strip(),
        max_video_seconds=_int("MAX_VIDEO_SECONDS", 10800),
        chunk_seconds=_int("CHUNK_SECONDS", 1200),
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
