"""Per-request UUID middleware and async context variable helpers.

Sets a unique request_id on each request, stores it in a ContextVar so it is
accessible to any logger running in the same async task, and echoes it back to
the caller via the X-Request-ID response header.

Access logging for non-health paths is also emitted here so that every request
produces a structured log entry without duplicating uvicorn's own access log.
"""

import contextvars
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the request ID for the current async task, or '' if unset."""
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        # Skip health checks from access log to avoid noise in high-frequency
        # monitoring setups.
        if request.url.path != "/api/health":
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": (request.client.host if request.client else ""),
                },
            )

        return response
