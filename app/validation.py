from __future__ import annotations

from urllib.parse import urlparse


ALLOWED_FACEBOOK_HOSTS = {
    "facebook.com",
    "fb.watch",
}


def validate_facebook_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A Facebook video URL is required")

    value = url.strip()
    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https")

    host = (parsed.hostname or "").lower().rstrip(".")
    is_facebook = host in ALLOWED_FACEBOOK_HOSTS or host.endswith(".facebook.com")

    if not is_facebook:
        raise ValueError("Only facebook.com and fb.watch URLs are supported in V1")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed")

    return value
