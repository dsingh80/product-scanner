"""Unit tests for Playwright fetcher (mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.errors import AppError, ErrorCode
from app.services.fetcher import _map_playwright_error, fetch_page


class TestFetcherErrorMapping:
    def test_dns_error(self):
        err = _map_playwright_error(Exception("net::ERR_NAME_NOT_RESOLVED"))
        assert err.code == ErrorCode.FETCH_DNS_ERROR

    def test_tls_error(self):
        err = _map_playwright_error(Exception("net::ERR_CERT_AUTHORITY_INVALID"))
        assert err.code == ErrorCode.FETCH_TLS_ERROR

    def test_timeout_error(self):
        err = _map_playwright_error(Exception("Timeout 30000ms exceeded"))
        assert err.code == ErrorCode.FETCH_TIMEOUT

    def test_blocked_error(self):
        err = _map_playwright_error(Exception("net::ERR_BLOCKED_BY_CLIENT"))
        assert err.code == ErrorCode.FETCH_BLOCKED


class TestFetchPage:
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        mock_page.url = "https://example.com"
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with patch("app.services.fetcher.get_browser", return_value=mock_browser):
            html, url, status = await fetch_page("https://example.com")
            assert status == 200
            assert "Test" in html
            assert url == "https://example.com"

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        mock_page = AsyncMock()
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {"content-type": "text/html"}
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with patch("app.services.fetcher.get_browser", return_value=mock_browser):
            with pytest.raises(AppError) as exc:
                await fetch_page("https://example.com/missing")
            assert exc.value.code == ErrorCode.FETCH_HTTP_ERROR

    @pytest.mark.asyncio
    async def test_fetch_not_html(self):
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value='{"json": true}')
        mock_page.url = "https://example.com/api"
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with patch("app.services.fetcher.get_browser", return_value=mock_browser):
            with pytest.raises(AppError) as exc:
                await fetch_page("https://example.com/api")
            assert exc.value.code == ErrorCode.FETCH_NOT_HTML
