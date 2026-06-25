"""API route handlers."""

import time

from fastapi import APIRouter, Request

from app.config import get_settings
from app.errors import AppError
from app.middleware.rate_limit import limiter
from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyze_product
from app.services.fetcher import check_playwright_health
from app.services.llm.models import check_llm_configured

router = APIRouter(prefix="/api")


@router.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    settings = get_settings()
    playwright = await check_playwright_health()
    llm = check_llm_configured(settings)
    return {
        "status": "ok",
        "playwright": playwright,
        "llm": llm,
        "timestamp": time.time(),
    }


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(lambda: f"{get_settings().rate_limit_per_minute}/minute")
@limiter.limit(lambda: f"{get_settings().rate_limit_per_hour}/hour")
async def analyze(request: Request, body: AnalyzeRequest):
    settings = get_settings()
    return await analyze_product(body, settings)
