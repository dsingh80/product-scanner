"""LangChain LLM model factory and provider fallback."""

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings
from app.errors import AppError, ErrorCode

ProviderName = Literal["anthropic", "openai"]

FALLBACK_ERROR_MARKERS = (
    "insufficient_quota",
    "rate_limit",
    "rate limit",
    "overloaded",
    "529",
    "503",
    "429",
    "too many requests",
    "capacity",
    "temporarily unavailable",
)


def _has_api_key(settings: Settings, provider: ProviderName) -> bool:
    if provider == "anthropic":
        return bool(settings.anthropic_api_key)
    return bool(settings.openai_api_key)


def get_provider_order(settings: Settings) -> list[ProviderName]:
    """Return configured providers in priority order."""
    if settings.llm_provider == "openai":
        order: list[ProviderName] = ["openai"]
    elif settings.llm_provider == "anthropic":
        order = ["anthropic"]
    else:
        order = ["anthropic", "openai"]
    return [provider for provider in order if _has_api_key(settings, provider)]


def is_fallback_worthy(exc: Exception) -> bool:
    """True when a later provider may succeed (quota, rate limits, overload)."""
    message = str(exc).lower()
    return any(marker in message for marker in FALLBACK_ERROR_MARKERS)


def create_llm(settings: Settings, provider: ProviderName) -> BaseChatModel:
    if provider == "openai":
        if not settings.openai_api_key:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "OpenAI API key not configured",
                status_code=503,
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )

    if not settings.anthropic_api_key:
        raise AppError(
            ErrorCode.LLM_NOT_CONFIGURED,
            "Anthropic API key not configured",
            status_code=503,
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
    )


def check_llm_configured(settings: Settings) -> dict:
    order = get_provider_order(settings)
    primary = order[0] if order else None
    fallback = order[1] if len(order) > 1 else None

    if primary == "anthropic":
        model = settings.anthropic_model
    elif primary == "openai":
        model = settings.openai_model
    else:
        model = None

    return {
        "provider": primary,
        "fallback_provider": fallback,
        "mode": settings.llm_provider,
        "model": model,
        "configured": bool(order),
        "status": "ok" if order else "not_configured",
    }
