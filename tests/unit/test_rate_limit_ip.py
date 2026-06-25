"""Unit tests for proxy-aware client IP extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.middleware.rate_limit import get_client_ip


def _make_request(headers: dict[str, str], remote_host: str = "1.2.3.4") -> MagicMock:
    request = MagicMock()
    request.headers = headers
    request.client = MagicMock()
    request.client.host = remote_host
    return request


class TestGetClientIp:
    def test_uses_remote_addr_when_trust_disabled(self):
        with patch("app.middleware.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.trust_proxy_headers = False
            request = _make_request({"X-Real-IP": "10.0.0.1"}, remote_host="1.2.3.4")
            ip = get_client_ip(request)
        assert ip == "1.2.3.4"

    def test_uses_x_real_ip_when_trust_enabled(self):
        with patch("app.middleware.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.trust_proxy_headers = True
            request = _make_request({"X-Real-IP": "5.6.7.8"}, remote_host="127.0.0.1")
            ip = get_client_ip(request)
        assert ip == "5.6.7.8"

    def test_falls_back_to_x_forwarded_for_when_no_x_real_ip(self):
        with patch("app.middleware.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.trust_proxy_headers = True
            request = _make_request(
                {"X-Forwarded-For": "9.10.11.12, 127.0.0.1"},
                remote_host="127.0.0.1",
            )
            ip = get_client_ip(request)
        assert ip == "9.10.11.12"

    def test_x_forwarded_for_first_hop_only(self):
        with patch("app.middleware.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.trust_proxy_headers = True
            request = _make_request(
                {"X-Forwarded-For": "  203.0.113.5 , 10.0.0.1, 127.0.0.1"},
                remote_host="127.0.0.1",
            )
            ip = get_client_ip(request)
        assert ip == "203.0.113.5"

    def test_ignores_x_real_ip_when_trust_disabled(self):
        with patch("app.middleware.rate_limit.get_settings") as mock_settings:
            mock_settings.return_value.trust_proxy_headers = False
            request = _make_request({"X-Real-IP": "5.6.7.8"}, remote_host="127.0.0.1")
            ip = get_client_ip(request)
        # Should return the socket address, not the spoofed header
        assert ip == "127.0.0.1"
