"""Pydantic request/response models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class PageContentInput(BaseModel):
    """Product page data captured in the user's browser (bypasses server fetch)."""

    url: str | None = Field(default=None, max_length=2048)
    html: str | None = Field(default=None, max_length=500_000)
    text: str | None = Field(default=None, max_length=200_000)
    title: str | None = Field(default=None, max_length=512)
    json_ld: list[Any] | None = None
    source: Literal["bookmarklet", "paste", "extension"] | None = None


class AnalyzeRequest(BaseModel):
    vehicle: str = Field(..., min_length=1, max_length=512)
    url: HttpUrl | None = None
    page_content: PageContentInput | None = None

    @model_validator(mode="after")
    def require_one_source(self) -> "AnalyzeRequest":
        has_url = self.url is not None
        has_content = self.page_content is not None and bool(
            (self.page_content.html or "").strip() or (self.page_content.text or "").strip()
        )
        if has_url and has_content:
            # Prefer client-captured content when both are sent (bookmarklet flow).
            self.url = None
            return self
        if not has_url and not has_content:
            raise ValueError("Provide a product url or page_content with html/text from the browser")
        return self


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class StageUsage(BaseModel):
    extract: TokenUsage = Field(default_factory=TokenUsage)
    analyze: TokenUsage = Field(default_factory=TokenUsage)


class Timings(BaseModel):
    validate_ms: float = 0
    fetch_ms: float = 0
    extract_ms: float = 0
    prefilter_ms: float = 0
    llm_extract_ms: float = 0
    llm_analyze_ms: float = 0
    total_ms: float = 0


class ProductInfo(BaseModel):
    name: str | None = None
    brand: str | None = None
    sku: str | None = None
    description: str | None = None
    category: str | None = None
    source_url: str | None = None


class CompatibilityResult(BaseModel):
    compatible: bool | None = None
    confidence: Literal["high", "medium", "low", "none"] = "none"
    summary: str = ""
    matched_vehicles: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    fitment_found: bool = False


class AnalyzeResponse(BaseModel):
    product: ProductInfo
    compatibility: CompatibilityResult
    usage: StageUsage = Field(default_factory=StageUsage)
    timings: Timings = Field(default_factory=Timings)
    raw_extract: dict[str, Any] | None = None
    source: Literal["url_fetch", "client_content"] = "url_fetch"
