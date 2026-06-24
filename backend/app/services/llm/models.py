"""LangChain LLM model factory."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings
from app.errors import AppError, ErrorCode


def create_llm(settings: Settings) -> BaseChatModel:
    if settings.llm_provider == "openai":
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

    if settings.llm_provider == "anthropic":
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

    raise AppError(
        ErrorCode.LLM_NOT_CONFIGURED,
        f"Unknown LLM provider: {settings.llm_provider}",
        status_code=503,
    )


def check_llm_configured(settings: Settings) -> dict:
    if settings.llm_provider == "openai":
        configured = bool(settings.openai_api_key)
        model = settings.openai_model
    elif settings.llm_provider == "anthropic":
        configured = bool(settings.anthropic_api_key)
        model = settings.anthropic_model
    else:
        configured = False
        model = None

    return {
        "provider": settings.llm_provider,
        "model": model,
        "configured": configured,
        "status": "ok" if configured else "not_configured",
    }
