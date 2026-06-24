"""Two-stage LangChain LCEL pipeline: extract → analyze."""

import time
from typing import Any

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import (
    CompatibilityResult,
    ProductInfo,
    StageUsage,
    TokenUsage,
)
from app.services.llm.callbacks import TokenUsageCallback
from app.services.llm.chains.analyze import build_analyze_chain
from app.services.llm.chains.extract import build_extract_chain
from app.services.llm.models import create_llm


class LLMPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None
        self._extract_chain = None
        self._analyze_chain = None

    def _ensure_chains(self):
        if self._extract_chain is not None:
            return
        self._llm = create_llm(self.settings)
        self._extract_chain = build_extract_chain(self._llm)
        self._analyze_chain = build_analyze_chain(self._llm)

    async def run(
        self,
        content: str,
        vehicle: str,
        source_url: str,
    ) -> tuple[ProductInfo, CompatibilityResult, StageUsage, dict[str, float]]:
        self._ensure_chains()
        usage = StageUsage()
        timings: dict[str, float] = {"llm_extract_ms": 0, "llm_analyze_ms": 0}

        extract_cb = TokenUsageCallback()
        t0 = time.perf_counter()
        try:
            extract_result: dict[str, Any] = await self._extract_chain.ainvoke(
                {"content": content},
                config={"callbacks": [extract_cb]},
            )
        except Exception as exc:
            raise AppError(ErrorCode.LLM_ERROR, f"Extract stage failed: {exc}", status_code=502) from exc
        timings["llm_extract_ms"] = (time.perf_counter() - t0) * 1000
        usage.extract = extract_cb.usage

        product = ProductInfo(
            name=extract_result.get("name"),
            brand=extract_result.get("brand"),
            sku=extract_result.get("sku"),
            description=extract_result.get("description"),
            category=extract_result.get("category"),
            source_url=source_url,
        )

        has_fitment = extract_result.get("has_fitment", False)
        fitment_data = extract_result.get("fitment_data") or []

        if not has_fitment and not fitment_data:
            compatibility = CompatibilityResult(
                compatible=None,
                confidence="none",
                summary="No vehicle fitment data found on the product page.",
                matched_vehicles=[],
                notes=["Early exit: no fitment information detected."],
                fitment_found=False,
            )
            return product, compatibility, usage, timings

        analyze_cb = TokenUsageCallback()
        t1 = time.perf_counter()
        try:
            analyze_result: dict[str, Any] = await self._analyze_chain.ainvoke(
                {
                    "product_json": product.model_dump_json(),
                    "vehicle_description": vehicle.strip(),
                    "fitment_data": "\n".join(fitment_data) if fitment_data else content[:2000],
                },
                config={"callbacks": [analyze_cb]},
            )
        except Exception as exc:
            raise AppError(ErrorCode.LLM_ERROR, f"Analyze stage failed: {exc}", status_code=502) from exc
        timings["llm_analyze_ms"] = (time.perf_counter() - t1) * 1000
        usage.analyze = analyze_cb.usage

        compatibility = CompatibilityResult(
            compatible=analyze_result.get("compatible"),
            confidence=analyze_result.get("confidence", "none"),
            summary=analyze_result.get("summary", ""),
            matched_vehicles=analyze_result.get("matched_vehicles") or [],
            notes=analyze_result.get("notes") or [],
            fitment_found=analyze_result.get("fitment_found", True),
        )
        return product, compatibility, usage, timings


def create_pipeline(settings: Settings) -> LLMPipeline:
    return LLMPipeline(settings)
