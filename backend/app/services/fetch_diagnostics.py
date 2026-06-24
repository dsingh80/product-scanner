"""Analyze fetch responses to diagnose HTTP errors and bot protection."""

import re
from typing import Any

# (vendor_id, human name, patterns matched against HTML/title lowercased)
_BOT_SIGNATURES: list[tuple[str, str, tuple[str, ...]]] = [
    ("cloudflare", "Cloudflare", ("cloudflare", "cf-browser-verification", "challenge-platform", "just a moment")),
    ("incapsula", "Imperva Incapsula", ("incapsula", "_incapsula_resource", "incident_id", "request unsuccessful")),
    ("datadome", "DataDome", ("datadome", "captcha-delivery")),
    ("akamai", "Akamai", ("akamai", "access denied")),
    ("ebay", "eBay bot check", ("pardon our interruption", "checking your browser before you access ebay", "ebay-killbot")),
    ("amazon", "Amazon bot check", ("robot check", "enter the characters you see below", "api-services/support")),
    ("generic_captcha", "CAPTCHA challenge", ("captcha", "verify you are human", "are you a robot")),
]

_SAFE_HEADER_KEYS = frozenset({
    "content-type",
    "content-length",
    "server",
    "cf-ray",
    "cf-mitigated",
    "x-frame-options",
    "x-cache",
    "via",
    "location",
    "retry-after",
    "x-ebay-c-extension",
})


def detect_bot_protection(html: str, title: str | None = None) -> dict[str, Any]:
    haystack = (html or "").lower()
    if title:
        haystack += " " + str(title).lower()

    for vendor_id, vendor_name, patterns in _BOT_SIGNATURES:
        matched = [p for p in patterns if p in haystack]
        if matched:
            return {
                "detected": True,
                "vendor": vendor_id,
                "vendor_name": vendor_name,
                "matched_signals": matched,
            }

    # Very small HTML with iframe-only body often means WAF interstitial
    if len(html or "") < 2500 and re.search(r"<iframe[^>]+id=[\"']main-iframe", html or "", re.I):
        return {
            "detected": True,
            "vendor": "waf_iframe",
            "vendor_name": "WAF interstitial (iframe)",
            "matched_signals": ["small_html_iframe_shell"],
        }

    return {"detected": False, "vendor": None, "vendor_name": None, "matched_signals": []}


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers.items():
        lk = key.lower()
        if lk in _SAFE_HEADER_KEYS:
            out[lk] = value[:256]
    return out


def _body_preview(html: str, limit: int = 1200) -> str:
    if not html:
        return ""
    collapsed = re.sub(r"\s+", " ", html).strip()
    return collapsed[:limit] + ("…" if len(collapsed) > limit else "")


def build_suggestions(
    status: int,
    bot: dict[str, Any],
    requested_url: str,
) -> list[str]:
    suggestions: list[str] = []

    if bot.get("detected"):
        vendor = bot.get("vendor_name") or "Bot protection"
        suggestions.append(
            f"{vendor} appears to be blocking automated browser access — "
            "the listing may work in a normal browser but not from this server."
        )
        suggestions.append("Use the FitCheck bookmarklet or paste page text from your browser.")
    elif status == 403:
        suggestions.append(
            "HTTP 403 Forbidden — the server rejected our request. This is common for "
            "marketplaces (eBay, Amazon) when they detect headless browsers."
        )
        suggestions.append("Use the FitCheck bookmarklet or paste page text from your browser.")
    elif status == 404:
        suggestions.append("The product page was not found — verify the URL is still valid.")
    elif status >= 500:
        suggestions.append("The remote server errored — try again later.")

    host = requested_url.split("/")[2] if "/" in requested_url else ""
    if "ebay." in host and status in (403, 401):
        suggestions.append(
            "eBay aggressively blocks scrapers. Use the bookmarklet while viewing the listing, "
            "or try a direct manufacturer/retailer page."
        )

    if not suggestions:
        suggestions.append("Set DEBUG=true in .env for full response headers and body preview.")

    return suggestions


def build_fetch_diagnostics(
    *,
    requested_url: str,
    final_url: str,
    status: int,
    headers: dict[str, str],
    html: str,
    title: str | None,
    user_agent: str,
    debug: bool,
) -> dict[str, Any]:
    bot = detect_bot_protection(html, title)
    diag: dict[str, Any] = {
        "requested_url": requested_url,
        "final_url": final_url,
        "redirected": requested_url.rstrip("/") != final_url.rstrip("/"),
        "http_status": status,
        "content_type": headers.get("content-type") or headers.get("Content-Type"),
        "html_length": len(html or ""),
        "page_title": title,
        "bot_protection": bot,
        "user_agent": user_agent,
        "suggestions": build_suggestions(status, bot, requested_url),
    }

    if debug:
        diag["response_headers"] = _sanitize_headers(headers)
        diag["body_preview"] = _body_preview(html)
        diag["visible_text_preview"] = _extract_visible_text_preview(html)

    return diag


def _extract_visible_text_preview(html: str, limit: int = 500) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def user_facing_fetch_message(status: int, bot: dict[str, Any]) -> str:
    if bot.get("detected"):
        vendor = bot.get("vendor_name") or "Bot protection"
        return f"{vendor} blocked automated access (HTTP {status})"
    if status == 403:
        return "Access forbidden (HTTP 403) — site likely blocks automated fetching"
    if status == 401:
        return "Unauthorized (HTTP 401)"
    return f"HTTP error {status}"
