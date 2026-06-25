"""Rate limiting middleware.

When deployed behind a reverse proxy (Nginx/Caddy), set TRUST_PROXY_HEADERS=true
so that per-IP limits apply to real client IPs read from X-Real-IP or the first
hop of X-Forwarded-For, rather than the proxy's loopback address.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Return the effective client IP, respecting proxy headers when configured."""
    from app.config import get_settings

    if get_settings().trust_proxy_headers:
        x_real_ip = request.headers.get("X-Real-IP", "").strip()
        if x_real_ip:
            return x_real_ip
        x_forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip)
