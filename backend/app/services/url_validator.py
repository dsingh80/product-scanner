"""SSRF-safe URL validation."""

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import get_settings
from app.errors import AppError, ErrorCode

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "metadata.google.internal",
    "169.254.169.254",
}


def _is_private_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        )
    except ValueError:
        return False


def _resolve_host_ips(hostname: str) -> list[str]:
    try:
        results = socket.getaddrinfo(hostname, None)
        return list({r[4][0] for r in results})
    except socket.gaierror:
        return []


def validate_url(url: str) -> str:
    """Validate URL for SSRF protection. Returns normalized URL string."""
    settings = get_settings()

    if len(url) > settings.max_url_length:
        raise AppError(
            ErrorCode.URL_TOO_LONG,
            f"URL exceeds maximum length of {settings.max_url_length} characters",
            status_code=400,
        )

    parsed = urlparse(url.strip())

    if not parsed.scheme:
        raise AppError(
            ErrorCode.URL_MALFORMED,
            "URL must include a scheme (http or https)",
            status_code=400,
        )

    scheme = parsed.scheme.lower()
    if scheme == "file":
        raise AppError(
            ErrorCode.URL_BLOCKED_FILE,
            "file:// URLs are not allowed",
            status_code=400,
        )

    if scheme not in ALLOWED_SCHEMES:
        raise AppError(
            ErrorCode.URL_INVALID_SCHEME,
            f"Scheme '{scheme}' is not allowed. Use http or https.",
            status_code=400,
        )

    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise AppError(
            ErrorCode.URL_MALFORMED,
            "URL must include a valid hostname",
            status_code=400,
        )

    if hostname in BLOCKED_HOSTNAMES:
        raise AppError(
            ErrorCode.URL_BLOCKED_LOCALHOST,
            "Localhost and loopback addresses are not allowed",
            status_code=400,
        )

    if hostname.endswith(".local") or hostname.endswith(".internal"):
        raise AppError(
            ErrorCode.URL_BLOCKED_INTERNAL,
            "Internal hostnames are not allowed",
            status_code=400,
        )

    if _is_private_ip(hostname):
        raise AppError(
            ErrorCode.URL_BLOCKED_PRIVATE_IP,
            "Private IP addresses are not allowed",
            status_code=400,
        )

    for ip in _resolve_host_ips(hostname):
        if _is_private_ip(ip):
            raise AppError(
                ErrorCode.URL_BLOCKED_PRIVATE_IP,
                f"Hostname resolves to blocked private IP: {ip}",
                status_code=400,
            )

    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        raise AppError(
            ErrorCode.URL_BLOCKED_INTERNAL,
            f"Port {port} is not allowed",
            status_code=400,
        )

    normalized = parsed.geturl()
    return normalized
