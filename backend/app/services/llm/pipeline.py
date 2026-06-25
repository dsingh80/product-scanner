"""Two-stage LangChain LCEL pipeline: extract → analyze."""

import logging
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
from app.services.llm.models import ProviderName, create_llm, get_provider_order, is_fallback_worthy
from app.services.security.injection_guard import scan_llm_output

logger = logging.getLogger(__name__)


class LLMPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._chains: dict[tuple[ProviderName, str], Any] = {}

    def _get_chain(self, provider: ProviderName, stage: str):
        key = (provider, stage)
        if key not in self._chains:
            llm = create_llm(self.settings, provider)
            if stage == "extract":
                self._chains[key] = build_extract_chain(llm)
            else:
                self._chains[key] = build_analyze_chain(llm)
        return self._chains[key]

    async def _invoke_with_fallback(
        self,
        stage: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], TokenUsage, ProviderName]:
        providers = get_provider_order(self.settings)
        if not providers:
            raise AppError(
                ErrorCode.LLM_NOT_CONFIGURED,
                "No LLM API keys configured",
                status_code=503,
            )

        last_exc: Exception | None = None
        for index, provider in enumerate(providers):
            callback = TokenUsageCallback()
            chain = self._get_chain(provider, stage)
            try:
                result: dict[str, Any] = await chain.ainvoke(
                    payload,
                    config={"callbacks": [callback]},
                )
                return result, callback.usage, provider
            except AppError:
                raise
            except Exception as exc:
                last_exc = exc
                has_fallback = index < len(providers) - 1
                if has_fallback and is_fallback_worthy(exc):
                    continue
                raise AppError(
                    ErrorCode.LLM_ERROR,
                    f"AI processing failed at {stage} stage."
                    if not self.settings.debug
                    else f"{stage.capitalize()} stage failed: {exc}",
                    status_code=502,
                    details={
                        "stage": stage,
                        "provider_attempted": provider,
                        "retryable": is_fallback_worthy(exc),
                        **({"error": str(exc)[:200]} if self.settings.debug else {}),
                    },
                ) from exc

        raise AppError(
            ErrorCode.LLM_ERROR,
            f"AI processing failed at {stage} stage."
            if not self.settings.debug
            else f"{stage.capitalize()} stage failed: {last_exc}",
            status_code=502,
            details={
                "stage": stage,
                "retryable": False,
                **({"error": str(last_exc)[:200]} if self.settings.debug else {}),
            },
        ) from last_exc

    async def run(
        self,
        content: str,
        vehicle: str,
        source_url: str,
    ) -> tuple[ProductInfo, CompatibilityResult, StageUsage, dict[str, float]]:
        usage = StageUsage()
        timings: dict[str, float] = {"llm_extract_ms": 0, "llm_analyze_ms": 0}

        _safe_compatibility = CompatibilityResult(
            compatible=None,
            confidence="none",
            summary="Analysis could not be completed.",
            matched_vehicles=[],
            notes=[],
            fitment_found=False,
        )

        t0 = time.perf_counter()
        extract_result, extract_usage, _extract_provider = await self._invoke_with_fallback(
            "extract",
            {"content": content},
        )
        timings["llm_extract_ms"] = (time.perf_counter() - t0) * 1000
        usage.extract = extract_usage

        # Scan LLM output for signs of prompt-leak or manipulation.
        extract_scan = scan_llm_output(extract_result)
        if extract_scan.blocked:
            logger.warning(
                "llm_output_blocked",
                extra={"stage": "extract", "field": extract_scan.field_name},
            )
            return ProductInfo(source_url=source_url), _safe_compatibility, usage, timings

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

        t1 = time.perf_counter()
        analyze_result, analyze_usage, _analyze_provider = await self._invoke_with_fallback(
            "analyze",
            {
                "product_json": product.model_dump_json(),
                "vehicle_description": vehicle.strip(),
                "fitment_data": "\n".join(fitment_data) if fitment_data else content[:2000],
            },
        )
        timings["llm_analyze_ms"] = (time.perf_counter() - t1) * 1000
        usage.analyze = analyze_usage

        analyze_scan = scan_llm_output(analyze_result)
        if analyze_scan.blocked:
            logger.warning(
                "llm_output_blocked",
                extra={"stage": "analyze", "field": analyze_scan.field_name},
            )
            return product, _safe_compatibility, usage, timings

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
