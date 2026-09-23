from __future__ import annotations

import hmac
import json
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import settings
from .service import transcribe_facebook


mcp = MCPServer(
    "SoftNest Transcript MCP",
    instructions=(
        "Use transcribe_facebook_video when the user provides a Facebook video or reel URL "
        "and asks for a transcript. Only process content the user is authorized to access."
    ),
)


@mcp.tool()
async def transcribe_facebook_video(
    url: str,
    language: str = "auto",
    timestamps: bool = False,
) -> dict[str, Any]:
    """Transcribe a public or authorized Facebook video/reel URL.

    Args:
        url: Facebook video, reel, watch, share, or fb.watch URL.
        language: ISO-639-1 language code such as en or nl, or 'auto'.
        timestamps: Include segment timestamps. Timestamp mode uses the configured timestamp model.
    """
    try:
        return await transcribe_facebook(
            url,
            language=language,
            timestamps=timestamps,
        )
    except Exception as exc:
        return {
            "success": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "softnest-transcript-mcp"})


@mcp.custom_route("/v1/transcribe", methods=["POST"])
async def rest_transcribe(request: Request) -> Response:
    # Custom routes are not protected by MCP auth automatically, so validate here too.
    if settings.service_api_key:
        auth = request.headers.get("authorization", "")
        expected = f"Bearer {settings.service_api_key}"
        if not hmac.compare_digest(auth, expected):
            return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"success": False, "message": "Invalid JSON"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"success": False, "message": "JSON object required"}, status_code=400)

    try:
        result = await transcribe_facebook(
            str(payload.get("url", "")),
            language=str(payload.get("language", "auto")),
            timestamps=bool(payload.get("timestamps", False)),
        )
        return JSONResponse(result)
    except Exception as exc:
        return JSONResponse(
            {
                "success": False,
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status_code=422,
        )


class BearerAuthMiddleware:
    """Optional bearer protection for MCP requests; /health remains public."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not settings.service_api_key or scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/health", "/v1/transcribe"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        expected = f"Bearer {settings.service_api_key}"
        if not hmac.compare_digest(headers.get("authorization", ""), expected):
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def build_app() -> ASGIApp:
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )
    app = mcp.streamable_http_app(
        host="0.0.0.0",
        json_response=True,
        stateless_http=True,
        transport_security=security,
    )
    return BearerAuthMiddleware(app)


app = build_app()
