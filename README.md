# SoftNest Transcript MCP

Docker-ready MCP service that accepts a Facebook video/reel URL, extracts audio with `yt-dlp` + `ffmpeg`, transcribes it with OpenAI, and returns a structured transcript.

## Endpoints

- MCP Streamable HTTP: `POST/GET/DELETE /mcp`
- REST helper: `POST /v1/transcribe`
- Health: `GET /health`

## MCP tool

`transcribe_facebook_video(url, language="auto", timestamps=false)`

Example result:

```json
{
  "success": true,
  "source": "facebook",
  "source_url": "https://www.facebook.com/reel/...",
  "title": "Example",
  "duration_seconds": 93.2,
  "language": "auto",
  "timestamps": false,
  "transcript": "...",
  "segments": [],
  "chunk_count": 1
}
```

## Quick start

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env

docker compose up -d --build
curl http://localhost:8000/health
```

REST test:

```bash
curl -X POST http://localhost:8000/v1/transcribe \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_SERVICE_API_KEY' \
  -d '{
    "url":"https://www.facebook.com/reel/VIDEO_ID",
    "language":"auto",
    "timestamps":false
  }'
```

If `SERVICE_API_KEY` is blank, bearer authentication is disabled. Set it before exposing this service publicly.

## Facebook access

V1 supports `facebook.com` subdomains and `fb.watch`. Public videos may work without authentication. For a video that legitimately requires your Facebook session, export a Netscape-format cookies file and mount it read-only into the container using `YTDLP_COOKIES_FILE`.

Do not use the service to bypass access controls or download/transcribe content you are not authorized to access.

## Long videos

The service re-encodes speech audio as mono 16 kHz MP3 and splits it into chunks before transcription. This avoids the OpenAI transcription upload limit for long recordings.

`CHUNK_SECONDS` defaults to 1200 seconds (20 minutes).

## Timestamps

Normal transcription uses `TRANSCRIPT_MODEL` (`gpt-transcribe` by default). If `timestamps=true`, the service uses `TIMESTAMP_MODEL` (`whisper-1` by default) and returns segment timestamps.

## Production behind Caddy / reverse proxy

Set `MCP_ALLOWED_HOSTS` to the hostname used by clients. Example:

```env
MCP_ALLOWED_HOSTS=transcript.soft-nest.com,transcript.soft-nest.com:*
SERVICE_API_KEY=replace-with-a-long-random-secret
```

The MCP Python SDK validates Host/Origin headers to protect against DNS rebinding. A deployment with the wrong allowlist will return HTTP 421.

A minimal Caddy route could proxy your public hostname to `softnest-transcript-mcp:8000`.

## Docker from a private GitHub repo

Once this repository is pushed to GitHub, Docker/Portainer can build directly from the Git repository. Keep `.env`, API keys, and Facebook cookies outside Git and inject them at deployment time.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall app
```
