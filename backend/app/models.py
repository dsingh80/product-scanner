"""Pydantic request/response models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    vehicle: str = Field(..., min_length=1, max_length=512)


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
