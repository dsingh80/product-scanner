"""Application configuration from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Product Vehicle Compatibility Scanner"
    debug: bool = False
    cors_origins: str = "*"
    rate_limit_per_minute: int = 10
    max_url_length: int = 2048
    fetch_timeout_ms: int = 30_000
    max_extract_chars: int = 12_000

    llm_provider: Literal["auto", "openai", "anthropic"] = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    playwright_headless: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
