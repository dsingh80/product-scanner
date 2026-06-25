"""Central error advice registry.

Maps each ErrorCode to a retryable flag and user-facing suggestions.
Called by exception handlers to enrich error responses without overwriting
domain-specific suggestions already added by the fetch layer.
"""

from typing import NamedTuple

from app.errors import AppError, ErrorCode


class ErrorAdvice(NamedTuple):
    retryable: bool
    suggestions: list[str]


_REGISTRY: dict[ErrorCode, ErrorAdvice] = {
    # URL validation
    ErrorCode.URL_INVALID_SCHEME: ErrorAdvice(
        retryable=False,
        suggestions=["Only https:// and http:// URLs are supported."],
    ),
    ErrorCode.URL_TOO_LONG: ErrorAdvice(
        retryable=False,
        suggestions=["The URL is too long. Paste the page content directly instead."],
    ),
    ErrorCode.URL_MALFORMED: ErrorAdvice(
        retryable=False,
        suggestions=["The URL looks malformed — check for typos or copy/paste errors."],
    ),
    ErrorCode.URL_BLOCKED_LOCALHOST: ErrorAdvice(
        retryable=False,
        suggestions=["Localhost URLs are blocked. Provide a public product page URL."],
    ),
    ErrorCode.URL_BLOCKED_PRIVATE_IP: ErrorAdvice(
        retryable=False,
        suggestions=["Private network addresses are blocked. Provide a public product page URL."],
    ),
    ErrorCode.URL_BLOCKED_FILE: ErrorAdvice(
        retryable=False,
        suggestions=["file:// URLs are not supported. Provide a public https:// URL."],
    ),
    ErrorCode.URL_BLOCKED_INTERNAL: ErrorAdvice(
        retryable=False,
        suggestions=["Internal hostnames are blocked. Provide a public product page URL."],
    ),
    # Fetch
    ErrorCode.FETCH_DNS_ERROR: ErrorAdvice(
        retryable=False,
        suggestions=["The domain could not be resolved. Check that the URL is spelled correctly."],
    ),
    ErrorCode.FETCH_TLS_ERROR: ErrorAdvice(
        retryable=False,
        suggestions=["The site has an SSL/TLS error. Verify the URL is correct and the site is reachable."],
    ),
    ErrorCode.FETCH_TIMEOUT: ErrorAdvice(
        retryable=True,
        suggestions=[
            "The page took too long to load. Try again, or use the bookmarklet/paste mode for slow sites.",
        ],
    ),
    ErrorCode.FETCH_HTTP_ERROR: ErrorAdvice(
        retryable=False,
        suggestions=["The server returned an error. Verify the URL points to a valid product page."],
    ),
    ErrorCode.FETCH_BLOCKED: ErrorAdvice(
        retryable=False,
        suggestions=["Automated access was blocked. Use the bookmarklet or paste page text from your browser."],
    ),
    ErrorCode.FETCH_NOT_HTML: ErrorAdvice(
        retryable=False,
        suggestions=["The URL does not point to an HTML page. Provide a direct product listing URL."],
    ),
    ErrorCode.FETCH_ERROR: ErrorAdvice(
        retryable=True,
        suggestions=["Page fetch failed. Try again or use bookmarklet/paste mode."],
    ),
    # Extraction
    ErrorCode.EXTRACT_EMPTY: ErrorAdvice(
        retryable=False,
        suggestions=[
            "No text content could be extracted from this page.",
            "Try the bookmarklet or paste mode to capture the page in your browser.",
        ],
    ),
    ErrorCode.EXTRACT_ERROR: ErrorAdvice(
        retryable=True,
        suggestions=["Content extraction failed unexpectedly. Try again."],
    ),
    # LLM
    ErrorCode.LLM_ERROR: ErrorAdvice(
        retryable=True,
        suggestions=[
            "The AI provider may be temporarily overloaded — try again shortly.",
            "Check /api/health to see the current LLM provider status.",
        ],
    ),
    ErrorCode.LLM_NOT_CONFIGURED: ErrorAdvice(
        retryable=False,
        suggestions=["The server is not configured with an AI provider API key — contact the operator."],
    ),
    # Rate limiting / server
    ErrorCode.RATE_LIMIT_EXCEEDED: ErrorAdvice(
        retryable=True,
        suggestions=[
            "You have sent too many requests. Wait a minute and try again.",
            "Avoid rapid repeated scans of the same URL.",
        ],
    ),
    ErrorCode.SERVER_BUSY: ErrorAdvice(
        retryable=True,
        suggestions=["The server is busy processing other requests. Try again in about 30 seconds."],
    ),
    ErrorCode.INTERNAL_ERROR: ErrorAdvice(
        retryable=True,
        suggestions=["An unexpected server error occurred. Try again — if it persists, contact support."],
    ),
    # Security
    ErrorCode.PROMPT_INJECTION_DETECTED: ErrorAdvice(
        retryable=False,
        suggestions=[
            "Your input was flagged for containing disallowed patterns.",
            "Use a normal product URL and vehicle description (e.g. '2020 Toyota Camry SE').",
        ],
    ),
}


def get_advice(code: ErrorCode) -> ErrorAdvice | None:
    return _REGISTRY.get(code)


def enrich_error(exc: AppError, request_id: str) -> AppError:
    """Attach advice and request ID to an AppError's details (non-destructive).

    Does not overwrite suggestions already set by domain-specific logic
    (e.g. the fetch layer's bot-detection suggestions).
    """
    details = dict(exc.details)
    details["request_id"] = request_id

    advice = get_advice(exc.code)
    if advice is not None:
        details["retryable"] = advice.retryable
        if "suggestions" not in details:
            details["suggestions"] = list(advice.suggestions)

    exc.details = details
    return exc
