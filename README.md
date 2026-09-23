# Transcript MCP

Docker-ready MCP service that accepts a Facebook video/reel URL, extracts its audio with `yt-dlp` + `ffmpeg`, transcribes it locally with `faster-whisper`, and returns a structured transcript.

No paid transcription API is required.

## How it works

```text
Facebook URL
    |
    v
yt-dlp
    |
    v
ffmpeg (mono 16 kHz audio)
    |
    v
faster-whisper / CTranslate2
    |
    v
MCP or REST transcript response
```

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
  "language": "en",
  "requested_language": "auto",
  "transcription_engine": "faster-whisper",
  "timestamps": false,
  "transcript": "...",
  "segments": [],
  "chunk_count": 1
}
```

## Quick start

```bash
cp .env.example .env
# Set SERVICE_API_KEY before exposing the service publicly.

docker compose up -d --build
curl http://localhost:8000/health
```

The default local transcription configuration is:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL_DIR=/models
```

The first transcription downloads the configured Whisper model. Docker stores it in the `whisper_models` named volume, so container rebuilds/restarts do not need to download it again.

For higher accuracy, try `WHISPER_MODEL=medium`. It requires more CPU, memory, disk space, and transcription time than `small`.

## ARM64

The image uses Python 3.12 and CTranslate2. Current CTranslate2 releases provide Linux AArch64 wheels, so this setup can run on an ARM64 Docker host without requiring an x86 container.

## REST test

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

## Local Whisper settings

```env
# Model name: tiny, base, small, medium, large-v3, etc.
WHISPER_MODEL=small

# Recommended for a CPU-only server.
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# Persistent model cache inside Docker.
WHISPER_MODEL_DIR=/models

# 0 lets CTranslate2 select the CPU thread count.
WHISPER_CPU_THREADS=0
WHISPER_NUM_WORKERS=1

# Accuracy/speed trade-off. Lower is faster.
WHISPER_BEAM_SIZE=5

# Skip long silent regions before transcription.
WHISPER_VAD_FILTER=true
```

## Facebook access

V1 supports `facebook.com` subdomains and `fb.watch`. Public videos may work without authentication. For a video that legitimately requires your Facebook session, export a Netscape-format cookies file and mount it read-only into the container using `YTDLP_COOKIES_FILE`.

Do not use the service to bypass access controls or download/transcribe content you are not authorized to access.

Example Compose addition:

```yaml
services:
  transcript-mcp:
    volumes:
      - whisper_models:/models
      - ./secrets/facebook_cookies.txt:/run/secrets/facebook_cookies.txt:ro
    environment:
      YTDLP_COOKIES_FILE: /run/secrets/facebook_cookies.txt
```

## Long videos

The service re-encodes speech audio as mono 16 kHz MP3 and splits long recordings into chunks before transcription. `CHUNK_SECONDS` defaults to 1200 seconds (20 minutes).

This is an operational choice for predictable local processing and timestamp offsets. It is not an external API upload limit.

## Timestamps

Set `timestamps=true` to return segment timestamps. Both normal and timestamped transcription use the same local faster-whisper model.

## Production behind Caddy

Set `MCP_ALLOWED_HOSTS` to the hostname used by clients. Example:

```env
MCP_ALLOWED_HOSTS=transcript.soft-nest.com,transcript.soft-nest.com:*
SERVICE_API_KEY=replace-with-a-long-random-secret
```

The MCP SDK validates Host/Origin headers to protect against DNS rebinding. A deployment with the wrong allowlist can return HTTP 421.

A minimal Caddy route can proxy your public hostname to `softnest-transcript-mcp:8000`.

## Updating

```bash
git pull
docker compose up -d --build
```

The `whisper_models` volume remains intact when the application container is recreated.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall app
```
