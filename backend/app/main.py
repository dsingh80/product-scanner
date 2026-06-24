"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.errors import AppError, ErrorCode
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import limiter
from app.routes.analyze import router as analyze_router
from app.services.fetcher import close_browser

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_browser()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    setup_cors(app, settings)

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_request: Request, _exc: RateLimitExceeded):
        error = AppError(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            "Rate limit exceeded. Try again later.",
            status_code=429,
        )
        return JSONResponse(status_code=429, content=error.to_dict())

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception):
        error = AppError(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred",
            status_code=500,
            details={"detail": str(exc)} if settings.debug else {},
        )
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
