"""Logging configuration: structured JSON lines to rotating file + stdout.

Call setup_logging() once at application startup (inside create_app()).
All application loggers inherit from the root logger configured here.

Log files rotate at maxBytes and up to backupCount old files are kept,
giving predictable on-disk usage (default ~100 MB total across 10 files).
"""

import json
import logging
import logging.handlers
import os
import sys
from typing import Any

_configured = False


class _JsonFormatter(logging.Formatter):
    """Render each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        # Late import so this module can be imported before the middleware
        # package is fully loaded.  After first call Python's import cache
        # makes this effectively free.
        try:
            from app.middleware.request_context import get_request_id

            rid = get_request_id()
        except Exception:
            rid = ""

        entry: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if rid:
            entry["request_id"] = rid

        # Structured fields attached via extra={...} on logging calls.
        for key in (
            "method",
            "path",
            "status",
            "duration_ms",
            "client_ip",
            "error_code",
            "stage",
            "provider",
            "field",
            "pattern_count",
            "source",
            "total_ms",
            "fetch_ms",
            "llm_ms",
            "total_tokens",
            "compatible",
        ):
            if hasattr(record, key):
                entry[key] = getattr(record, key)

        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


def setup_logging(
    log_dir: str = "",
    log_level: str = "INFO",
    max_bytes: int = 10_485_760,
    backup_count: int = 10,
) -> None:
    """Configure root logger with JSON-lines output to stdout and optional rotating file.

    Safe to call multiple times; subsequent calls are no-ops so test suites
    that call create_app() repeatedly do not accumulate duplicate handlers.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = _JsonFormatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Suppress noisy third-party access/debug logs; our middleware handles
    # per-request access logging so uvicorn's access log is redundant.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    _configured = True
