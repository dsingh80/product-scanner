"""Playwright-based page fetcher."""

import re
from typing import Any

from app.config import Settings, get_settings
from app.errors import AppError, ErrorCode
from app.services.fetch_diagnostics import detect_bot_protection, user_facing_fetch_message
from app.services.fetch_trace import build_fetch_trace
from app.services.site_handlers import blocked_site_suggestions

_browser: Any = None
_playwright: Any = None

REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


async def get_browser():
    global _browser, _playwright
    if _browser is None:
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        settings = get_settings()
        _browser = await _playwright.chromium.launch(headless=settings.playwright_headless)
    return _browser


async def close_browser():
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


def _map_playwright_error(exc: Exception, *, debug: bool = False) -> AppError:
    msg = str(exc).lower()
    details: dict[str, Any] = {}
    if debug:
        details["playwright_error"] = str(exc)[:500]

    if "net::err_name_not_resolved" in msg or "dns" in msg:
        return AppError(ErrorCode.FETCH_DNS_ERROR, "DNS resolution failed", status_code=502, details=details)
    if "net::err_cert" in msg or "ssl" in msg or "tls" in msg:
        return AppError(ErrorCode.FETCH_TLS_ERROR, "TLS/SSL certificate error", status_code=502, details=details)
    if "timeout" in msg:
        return AppError(ErrorCode.FETCH_TIMEOUT, "Page load timed out", status_code=504, details=details)
    if "net::err_blocked" in msg or "blocked" in msg:
        return AppError(ErrorCode.FETCH_BLOCKED, "Request was blocked", status_code=403, details=details)
    return AppError(ErrorCode.FETCH_ERROR, f"Failed to fetch page: {exc}", status_code=502, details=details)


def _raise_fetch_failure(
    *,
    requested_url: str,
    final_url: str,
    status: int,
    headers: dict[str, str],
    html: str,
    title: str | None,
    user_agent: str,
    debug: bool,
    request_headers: dict[str, str] | None = None,
) -> None:
    bot = detect_bot_protection(html, title)
    fetch_trace = build_fetch_trace(
        requested_url=requested_url,
        final_url=final_url,
        status=status,
        response_headers=headers,
        html=html,
        title=title,
        user_agent=user_agent,
        request_headers=request_headers,
    )

    if bot["detected"] or status == 403:
        code = ErrorCode.FETCH_BLOCKED
        http_status = 502
    elif status >= 400:
        code = ErrorCode.FETCH_HTTP_ERROR
        http_status = 502
    else:
        code = ErrorCode.FETCH_BLOCKED
        http_status = 502

    suggestions = blocked_site_suggestions(requested_url)
    if not bot.get("detected") and status not in (403, 401):
        suggestions.append("Set DEBUG=true in .env to see the raw fetch request/response.")

    details: dict[str, Any] = {
        "status_code": status,
        "final_url": final_url,
        "bot_protection": bot,
        "suggestions": suggestions,
    }
    if debug:
        details["fetch"] = fetch_trace
    elif bot.get("detected"):
        details["hint"] = suggestions[0] if suggestions else None

    raise AppError(
        code,
        user_facing_fetch_message(status, bot),
        status_code=http_status,
        details=details,
    )


async def _new_browser_context(browser, user_agent: str):
    context = await browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
        extra_http_headers=REQUEST_HEADERS,
    )
    return context


async def fetch_page(url: str) -> tuple[str, str, int]:
    """
    Fetch page HTML via Playwright.
    Returns (html, final_url, status_code).
    """
    settings = get_settings()
    debug = settings.debug
    user_agent = DEFAULT_USER_AGENT

    browser = await get_browser()
    context = await _new_browser_context(browser, user_agent)
    page = await context.new_page()

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=settings.fetch_timeout_ms,
        )
        if response is None:
            raise AppError(
                ErrorCode.FETCH_ERROR,
                "No response received",
                status_code=502,
                details={"fetch": {"request": {"url": url}}} if debug else {},
            )

        status = response.status
        headers = dict(response.headers)
        html = await page.content()
        final_url = page.url
        title = await page.title()

        if status >= 400:
            _raise_fetch_failure(
                requested_url=url,
                final_url=final_url,
                status=status,
                headers=headers,
                html=html,
                title=title,
                user_agent=user_agent,
                debug=debug,
                request_headers=REQUEST_HEADERS,
            )

        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

        await page.evaluate(
            """async () => {
                await new Promise(resolve => {
                    let total = 0;
                    const step = () => {
                        window.scrollBy(0, 400);
                        total += 400;
                        if (total < document.body.scrollHeight) {
                            setTimeout(step, 100);
                        } else {
                            resolve();
                        }
                    };
                    step();
                });
            }"""
        )
        await page.wait_for_timeout(500)

        html = await page.content()
        final_url = page.url
        title = await page.title()
        content_type = headers.get("content-type", "")

        bot = detect_bot_protection(html, title)
        if bot["detected"]:
            _raise_fetch_failure(
                requested_url=url,
                final_url=final_url,
                status=status,
                headers=headers,
                html=html,
                title=title,
                user_agent=user_agent,
                debug=debug,
                request_headers=REQUEST_HEADERS,
            )

        if "text/html" not in content_type.lower() and not re.search(r"<html", html, re.I):
            details: dict[str, Any] = {"content_type": content_type}
            if debug:
                details["fetch"] = build_fetch_trace(
                    requested_url=url,
                    final_url=final_url,
                    status=status,
                    response_headers=headers,
                    html=html,
                    title=title,
                    user_agent=user_agent,
                    request_headers=REQUEST_HEADERS,
                )
            raise AppError(
                ErrorCode.FETCH_NOT_HTML,
                "Response is not HTML content",
                status_code=422,
                details=details,
            )

        return html, final_url, status
    except AppError:
        raise
    except Exception as exc:
        raise _map_playwright_error(exc, debug=debug) from exc
    finally:
        await context.close()


async def check_playwright_health() -> dict[str, Any]:
    try:
        browser = await get_browser()
        return {"status": "ok", "browser_connected": browser.is_connected()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
