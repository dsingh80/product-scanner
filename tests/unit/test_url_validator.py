"""Unit tests for URL validator."""

import pytest

from app.errors import AppError, ErrorCode
from app.services.url_validator import validate_url


class TestUrlValidator:
    def test_valid_https_url(self):
        result = validate_url("https://example.com/product/123")
        assert result.startswith("https://example.com")

    def test_valid_http_url(self):
        result = validate_url("http://shop.example.com/item")
        assert "shop.example.com" in result

    def test_blocks_file_scheme(self):
        with pytest.raises(AppError) as exc:
            validate_url("file:///etc/passwd")
        assert exc.value.code == ErrorCode.URL_BLOCKED_FILE

    def test_blocks_localhost(self):
        with pytest.raises(AppError) as exc:
            validate_url("http://localhost/product")
        assert exc.value.code == ErrorCode.URL_BLOCKED_LOCALHOST

    def test_blocks_127_0_0_1(self):
        with pytest.raises(AppError) as exc:
            validate_url("http://127.0.0.1/admin")
        assert exc.value.code == ErrorCode.URL_BLOCKED_LOCALHOST

    def test_blocks_invalid_scheme(self):
        with pytest.raises(AppError) as exc:
            validate_url("ftp://example.com/file")
        assert exc.value.code == ErrorCode.URL_INVALID_SCHEME

    def test_blocks_url_too_long(self, monkeypatch):
        monkeypatch.setenv("MAX_URL_LENGTH", "50")
        from app.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(AppError) as exc:
            validate_url("https://example.com/" + "a" * 100)
        assert exc.value.code == ErrorCode.URL_TOO_LONG
        get_settings.cache_clear()

    def test_blocks_malformed_url(self):
        with pytest.raises(AppError) as exc:
            validate_url("not-a-url")
        assert exc.value.code == ErrorCode.URL_MALFORMED

    def test_blocks_internal_hostname(self):
        with pytest.raises(AppError) as exc:
            validate_url("https://server.local/product")
        assert exc.value.code == ErrorCode.URL_BLOCKED_INTERNAL
