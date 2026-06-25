"""Structured error codes and exceptions."""

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    # URL validation
    URL_INVALID_SCHEME = "URL_INVALID_SCHEME"
    URL_TOO_LONG = "URL_TOO_LONG"
    URL_MALFORMED = "URL_MALFORMED"
    URL_BLOCKED_LOCALHOST = "URL_BLOCKED_LOCALHOST"
    URL_BLOCKED_PRIVATE_IP = "URL_BLOCKED_PRIVATE_IP"
    URL_BLOCKED_FILE = "URL_BLOCKED_FILE"
    URL_BLOCKED_INTERNAL = "URL_BLOCKED_INTERNAL"

    # Fetch
    FETCH_DNS_ERROR = "FETCH_DNS_ERROR"
    FETCH_TLS_ERROR = "FETCH_TLS_ERROR"
    FETCH_TIMEOUT = "FETCH_TIMEOUT"
    FETCH_HTTP_ERROR = "FETCH_HTTP_ERROR"
    FETCH_BLOCKED = "FETCH_BLOCKED"
    FETCH_NOT_HTML = "FETCH_NOT_HTML"
    FETCH_ERROR = "FETCH_ERROR"

    # Extraction / processing
    EXTRACT_EMPTY = "EXTRACT_EMPTY"
    EXTRACT_ERROR = "EXTRACT_ERROR"

    # LLM
    LLM_ERROR = "LLM_ERROR"
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"

    # Rate limit / server
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVER_BUSY = "SERVER_BUSY"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Security
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                **({"details": self.details} if self.details else {}),
            }
        }
