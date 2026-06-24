"""Unit tests for fetch diagnostics."""

import pytest

from app.services.fetch_diagnostics import (
    build_fetch_diagnostics,
    detect_bot_protection,
    user_facing_fetch_message,
)


class TestDetectBotProtection:
    def test_cloudflare(self):
        html = "<html><title>Just a moment...</title><body>cf-browser-verification</body></html>"
        result = detect_bot_protection(html, "Just a moment...")
        assert result["detected"] is True
        assert result["vendor"] == "cloudflare"

    def test_incapsula_iframe_shell(self):
        html = (
            '<html><body><iframe id="main-iframe" src="/_Incapsula_Resource">'
            "blocked</iframe></body></html>"
        )
        result = detect_bot_protection(html)
        assert result["detected"] is True

    def test_ebay_block(self):
        html = "<html><body>Pardon Our Interruption. Checking your browser before you access eBay.</body></html>"
        result = detect_bot_protection(html)
        assert result["detected"] is True
        assert result["vendor"] == "ebay"

    def test_normal_product_page(self):
        html = "<html><body><h1>Brake Pads</h1><p>Fits 2014 Peterbilt 386</p></body></html>"
        result = detect_bot_protection(html, "Brake Pads")
        assert result["detected"] is False


class TestBuildFetchDiagnostics:
    def test_includes_suggestions_for_403(self):
        diag = build_fetch_diagnostics(
            requested_url="https://www.ebay.com/itm/123",
            final_url="https://www.ebay.com/itm/123",
            status=403,
            headers={"content-type": "text/html"},
            html="<html>Pardon our interruption</html>",
            title="Access Denied",
            user_agent="TestAgent",
            debug=True,
        )
        assert diag["http_status"] == 403
        assert diag["bot_protection"]["detected"] is True
        assert len(diag["suggestions"]) >= 1
        assert "response_headers" in diag
        assert "body_preview" in diag

    def test_debug_off_omits_body_preview(self):
        diag = build_fetch_diagnostics(
            requested_url="https://example.com",
            final_url="https://example.com",
            status=403,
            headers={},
            html="<html>blocked</html>",
            title=None,
            user_agent="TestAgent",
            debug=False,
        )
        assert "body_preview" not in diag
        assert "suggestions" in diag


class TestUserFacingMessage:
    def test_bot_block_message(self):
        bot = {"detected": True, "vendor_name": "eBay bot check"}
        assert "eBay" in user_facing_fetch_message(403, bot)

    def test_plain_403(self):
        assert "403" in user_facing_fetch_message(403, {"detected": False})
