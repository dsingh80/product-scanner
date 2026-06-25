"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.errors import AppError, ErrorCode
from app.logging_setup import setup_logging
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import get_client_ip, limiter
from app.middleware.request_context import RequestContextMiddleware
from app.routes.analyze import router as analyze_router
from app.services.error_advice import enrich_error
from app.services.fetcher import close_browser

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_browser()


def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging(
        log_dir=settings.log_dir,
        log_level=settings.log_level,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Starlette executes middlewares in reverse registration order (last added = outermost).
    # SlowAPI and CORS are added first (innermost), then RequestContextMiddleware last so
    # it is outermost — ensuring request_id is set before rate-limit or CORS handling runs.
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    setup_cors(app, settings)
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", "")
        enrich_error(exc, request_id)
        logger.warning(
            exc.message,
            extra={"error_code": exc.code.value, "status": exc.status_code},
        )
        response = JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        if exc.code == ErrorCode.SERVER_BUSY:
            response.headers["Retry-After"] = "30"
        return response

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, _exc: RateLimitExceeded):
        request_id = getattr(request.state, "request_id", "")
        client_ip = get_client_ip(request)
        logger.warning("rate_limit_exceeded", extra={"client_ip": client_ip})
        error = AppError(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            "Rate limit exceeded. Try again later.",
            status_code=429,
        )
        enrich_error(error, request_id)
        response = JSONResponse(status_code=429, content=error.to_dict())
        response.headers["Retry-After"] = "60"
        return response

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "")
        logger.error(
            f"Unhandled {type(exc).__name__}",
            exc_info=exc,
        )
        error = AppError(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred",
            status_code=500,
            details={"detail": str(exc)} if settings.debug else {},
        )
        enrich_error(error, request_id)
        return JSONResponse(status_code=500, content=error.to_dict())

    app.include_router(analyze_router)

    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
        demo_dir = FRONTEND_DIR / "demo"
        if demo_dir.exists():
            app.mount("/demo", StaticFiles(directory=demo_dir, html=True), name="demo")

        @app.get("/")
        async def index():
            return FileResponse(FRONTEND_DIR / "index.html")

    return app


app = create_app()
