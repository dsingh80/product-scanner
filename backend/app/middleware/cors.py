"""CORS configuration helper."""

from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings


def setup_cors(app, settings: Settings) -> None:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
