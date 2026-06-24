"""Orchestrates the full analyze pipeline."""

import time
from typing import Any

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.models import AnalyzeRequest, AnalyzeResponse, Timings
from app.services.extractor import extract_content, extract_from_client_content
from app.services.fetcher import fetch_page
from app.services.llm.pipeline import create_pipeline
from app.services.prefilter import prefilter_content
from app.services.site_handlers import detect_site
from app.services.url_validator import validate_url


async def analyze_product(request: AnalyzeRequest, settings: Settings) -> AnalyzeResponse:
    timings = Timings()
    t_total = time.perf_counter()
    debug = settings.debug

    source = "url_fetch"
    final_url: str
    html: str | None = None

    if request.page_content and (
        (request.page_content.html or "").strip() or (request.page_content.text or "").strip()
    ):
        source = "client_content"
        timings.validate_ms = 0
        timings.fetch_ms = 0
        pc = request.page_content
        final_url = (pc.url or "").strip() or "client://browser"

        t2 = time.perf_counter()
        extracted = extract_from_client_content(pc, final_url)
        timings.extract_ms = (time.perf_counter() - t2) * 1000
    else:
        if not request.url:
            raise AppError(
                ErrorCode.URL_MALFORMED,
                "Provide a product URL or page content from your browser",
                status_code=422,
            )

        t0 = time.perf_counter()
        url = validate_url(str(request.url))
        timings.validate_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        try:
            html, final_url, _status = await fetch_page(url)
        except AppError:
            # Fail fast — no LLM calls after fetch failure.
            raise
        timings.fetch_ms = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        extracted = extract_content(html, final_url)
        timings.extract_ms = (time.perf_counter() - t2) * 1000

    if not extracted.get("combined_text"):
        raise AppError(ErrorCode.EXTRACT_EMPTY, "No extractable content found on page", status_code=422)

    t3 = time.perf_counter()
    filtered = prefilter_content(extracted)
    timings.prefilter_ms = (time.perf_counter() - t3) * 1000

    pipeline = create_pipeline(settings)
    product, compatibility, usage, llm_timings = await pipeline.run(
        filtered, request.vehicle, final_url
    )
    timings.llm_extract_ms = llm_timings.get("llm_extract_ms", 0)
    timings.llm_analyze_ms = llm_timings.get("llm_analyze_ms", 0)
    timings.total_ms = (time.perf_counter() - t_total) * 1000

    raw_extract: dict[str, Any] | None = None
    if debug:
        raw_extract = {
            "source": source,
            "site": detect_site(final_url),
            "combined_text_chars": len(filtered),
        }

    return AnalyzeResponse(
        product=product,
        compatibility=compatibility,
        usage=usage,
        timings=timings,
        raw_extract=raw_extract,
        source=source,
    )
