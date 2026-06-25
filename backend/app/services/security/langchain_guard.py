"""LangChain LCEL guard runnable for prompt injection prevention.

Usage in chain construction:
    guard = make_input_guard("content")
    chain = guard | prompt | llm | parser

The guard scans the named input field before the prompt template is rendered.
Benign inputs pass through unchanged; injections raise AppError immediately
so no LLM tokens are spent.
"""

from typing import Any

from langchain_core.runnables import RunnableLambda

from app.errors import AppError, ErrorCode
from app.services.security.injection_guard import scan_text


def make_input_guard(field_key: str) -> RunnableLambda:
    """Return an LCEL-composable runnable that scans one input field.

    Args:
        field_key: The key in the chain's input dict to scan (e.g. "content").

    Returns:
        A RunnableLambda that either passes the dict through or raises
        AppError(PROMPT_INJECTION_DETECTED).
    """

    def _guard(inputs: dict[str, Any]) -> dict[str, Any]:
        text = inputs.get(field_key)
        if isinstance(text, str):
            result = scan_text(text, field_key)
            if result.blocked:
                raise AppError(
                    ErrorCode.PROMPT_INJECTION_DETECTED,
                    "Request blocked: potential prompt injection detected.",
                    status_code=400,
                    details={
                        "field": result.field_name,
                        "pattern_count": len(result.matched_patterns),
                    },
                )
        return inputs

    return RunnableLambda(_guard)
