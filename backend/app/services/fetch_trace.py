"""Structured fetch request/response trace for debug output."""

from typing import Any

from app.services.fetch_diagnostics import (
    _body_preview,
    _extract_visible_text_preview,
    _sanitize_headers,
    detect_bot_protection,
)


def build_fetch_trace(
    *,
    requested_url: str,
    final_url: str,
    status: int,
    response_headers: dict[str, str],
    html: str,
    title: str | None,
    user_agent: str,
    request_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    bot = detect_bot_protection(html, title)
    return {
        "request": {
            "method": "GET",
            "url": requested_url,
            "user_agent": user_agent,
            "headers": request_headers or {},
        },
        "response": {
            "status": status,
            "final_url": final_url,
            "redirected": requested_url.rstrip("/") != final_url.rstrip("/"),
            "headers": _sanitize_headers(response_headers),
            "content_type": response_headers.get("content-type") or response_headers.get("Content-Type"),
            "body_length": len(html or ""),
            "page_title": title,
            "body_preview": _body_preview(html, limit=8000),
            "visible_text_preview": _extract_visible_text_preview(html, limit=2000),
            "bot_protection": bot,
        },
    }
