"""Token usage tracking callbacks."""

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.models import TokenUsage


class TokenUsageCallback(BaseCallbackHandler):
    def __init__(self):
        self.usage = TokenUsage()

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            self.usage.input_tokens += token_usage.get("prompt_tokens", 0) or token_usage.get("input_tokens", 0)
            self.usage.output_tokens += token_usage.get("completion_tokens", 0) or token_usage.get("output_tokens", 0)
            self.usage.total_tokens += token_usage.get("total_tokens", 0) or (
                self.usage.input_tokens + self.usage.output_tokens
            )

    def reset(self) -> None:
        self.usage = TokenUsage()
