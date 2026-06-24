"""Playwright-based page fetcher."""

import re
import time
from typing import Any

from app.config import get_settings
from app.errors import AppError, ErrorCode

_browser: Any = None
_playwright: Any = None


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


def _map_playwright_error(exc: Exception) -> AppError:
    msg = str(exc).lower()
    if "net::err_name_not_resolved" in msg or "dns" in msg:
        return AppError(ErrorCode.FETCH_DNS_ERROR, "DNS resolution failed", status_code=502)
    if "net::err_cert" in msg or "ssl" in msg or "tls" in msg:
        return AppError(ErrorCode.FETCH_TLS_ERROR, "TLS/SSL certificate error", status_code=502)
    if "timeout" in msg:
        return AppError(ErrorCode.FETCH_TIMEOUT, "Page load timed out", status_code=504)
    if "net::err_blocked" in msg or "blocked" in msg:
        return AppError(ErrorCode.FETCH_BLOCKED, "Request was blocked", status_code=403)
    return AppError(ErrorCode.FETCH_ERROR, f"Failed to fetch page: {exc}", status_code=502)


async def fetch_page(url: str) -> tuple[str, str, int]:
    """
    Fetch page HTML via Playwright.
    Returns (html, final_url, status_code).
    """
    settings = get_settings()
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        ignore_https_errors=False,
    )
    page = await context.new_page()

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=settings.fetch_timeout_ms,
        )
        if response is None:
            raise AppError(ErrorCode.FETCH_ERROR, "No response received", status_code=502)

        status = response.status
        if status >= 400:
            raise AppError(
                ErrorCode.FETCH_HTTP_ERROR,
                f"HTTP error {status}",
                status_code=502,
                details={"status_code": status},
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

        content_type = response.headers.get("content-type", "")
        html = await page.content()
        final_url = page.url

        if "text/html" not in content_type.lower() and not re.search(r"<html", html, re.I):
            raise AppError(
                ErrorCode.FETCH_NOT_HTML,
                "Response is not HTML content",
                status_code=422,
            )

        return html, final_url, status
    except AppError:
        raise
    except Exception as exc:
        raise _map_playwright_error(exc) from exc
    finally:
        await context.close()


async def check_playwright_health() -> dict[str, Any]:
    try:
        browser = await get_browser()
        return {"status": "ok", "browser_connected": browser.is_connected()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
