"""Unit tests for the error advice registry and enrich_error helper."""

import pytest

from app.errors import AppError, ErrorCode
from app.services.error_advice import enrich_error, get_advice


class TestGetAdvice:
    def test_every_error_code_has_advice(self):
        """All ErrorCode values must have an entry in the registry."""
        for code in ErrorCode:
            advice = get_advice(code)
            assert advice is not None, f"No advice registered for {code}"
            assert len(advice.suggestions) > 0, f"No suggestions for {code}"

    def test_rate_limit_is_retryable(self):
        assert get_advice(ErrorCode.RATE_LIMIT_EXCEEDED).retryable is True

    def test_server_busy_is_retryable(self):
        assert get_advice(ErrorCode.SERVER_BUSY).retryable is True

    def test_llm_error_is_retryable(self):
        assert get_advice(ErrorCode.LLM_ERROR).retryable is True

    def test_fetch_timeout_is_retryable(self):
        assert get_advice(ErrorCode.FETCH_TIMEOUT).retryable is True

    def test_url_blocked_not_retryable(self):
        assert get_advice(ErrorCode.URL_BLOCKED_LOCALHOST).retryable is False

    def test_injection_not_retryable(self):
        assert get_advice(ErrorCode.PROMPT_INJECTION_DETECTED).retryable is False

    def test_llm_not_configured_not_retryable(self):
        assert get_advice(ErrorCode.LLM_NOT_CONFIGURED).retryable is False


class TestEnrichError:
    def test_adds_request_id(self):
        exc = AppError(ErrorCode.LLM_ERROR, "test", status_code=502)
        enrich_error(exc, "test-request-id")
        assert exc.details["request_id"] == "test-request-id"

    def test_adds_suggestions_when_absent(self):
        exc = AppError(ErrorCode.LLM_ERROR, "test", status_code=502)
        enrich_error(exc, "rid")
        assert "suggestions" in exc.details
        assert len(exc.details["suggestions"]) > 0

    def test_adds_retryable_flag(self):
        exc = AppError(ErrorCode.LLM_ERROR, "test", status_code=502)
        enrich_error(exc, "rid")
        assert exc.details["retryable"] is True

    def test_does_not_overwrite_existing_suggestions(self):
        original = ["existing suggestion from fetch layer"]
        exc = AppError(
            ErrorCode.FETCH_BLOCKED,
            "blocked",
            status_code=502,
            details={"suggestions": original},
        )
        enrich_error(exc, "rid")
        assert exc.details["suggestions"] == original

    def test_enriches_server_busy(self):
        exc = AppError(ErrorCode.SERVER_BUSY, "busy", status_code=503)
        enrich_error(exc, "rid")
        assert exc.details["retryable"] is True
        assert any("30" in s for s in exc.details["suggestions"])

    def test_enriches_injection_detected(self):
        exc = AppError(ErrorCode.PROMPT_INJECTION_DETECTED, "blocked", status_code=400)
        enrich_error(exc, "rid")
        assert exc.details["retryable"] is False
        assert exc.details["suggestions"]
