"""Unit tests for LLM provider selection and fallback."""

import pytest

from app.config import Settings
from app.services.llm.models import get_provider_order, is_fallback_worthy


class TestProviderOrder:
    def test_auto_prefers_anthropic_when_both_configured(self):
        settings = Settings(
            llm_provider="auto",
            anthropic_api_key="ant-key",
            openai_api_key="oai-key",
        )
        assert get_provider_order(settings) == ["anthropic", "openai"]

    def test_auto_skips_missing_anthropic_key(self):
        settings = Settings(
            llm_provider="auto",
            anthropic_api_key="",
            openai_api_key="oai-key",
        )
        assert get_provider_order(settings) == ["openai"]

    def test_anthropic_only_mode(self):
        settings = Settings(
            llm_provider="anthropic",
            anthropic_api_key="ant-key",
            openai_api_key="oai-key",
        )
        assert get_provider_order(settings) == ["anthropic"]

    def test_openai_only_mode(self):
        settings = Settings(
            llm_provider="openai",
            anthropic_api_key="ant-key",
            openai_api_key="oai-key",
        )
        assert get_provider_order(settings) == ["openai"]


class TestFallbackDetection:
    @pytest.mark.parametrize(
        "message",
        [
            "Error code: 429 - insufficient_quota",
            "rate_limit exceeded",
            "overloaded_error",
            "HTTP 503 temporarily unavailable",
        ],
    )
    def test_retryable_errors(self, message):
        assert is_fallback_worthy(RuntimeError(message)) is True

    def test_non_retryable_errors(self):
        assert is_fallback_worthy(RuntimeError("invalid api key")) is False
