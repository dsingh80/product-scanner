"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")


@pytest.fixture
def settings():
    from app.config import Settings

    return Settings(
        openai_api_key="test-key",
        llm_provider="openai",
        rate_limit_per_minute=1000,
    )


@pytest.fixture
def client():
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_html():
    fixtures_dir = Path(__file__).parent / "fixtures" / "pages"
    return (fixtures_dir / "product_with_fitment.html").read_text(encoding="utf-8")


@pytest.fixture
def mock_fetch(sample_html):
    with patch("app.services.analyzer.fetch_page", new_callable=AsyncMock) as mock:
        mock.return_value = (sample_html, "https://example.com/product/brake-pads", 200)
        yield mock


@pytest.fixture
def mock_llm_pipeline():
    from app.models import CompatibilityResult, ProductInfo, StageUsage, TokenUsage

    product = ProductInfo(
        name="Ceramic Brake Pads",
        brand="StopTech",
        sku="ST-1234",
        description="High performance brake pads",
        category="Brakes",
        source_url="https://example.com/product/brake-pads",
    )
    compatibility = CompatibilityResult(
        compatible=True,
        confidence="high",
        summary="Fits the specified vehicle.",
        matched_vehicles=["2020 Toyota Camry SE"],
        notes=["Verify trim level."],
        fitment_found=True,
    )
    usage = StageUsage(
        extract=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        analyze=TokenUsage(input_tokens=80, output_tokens=40, total_tokens=120),
    )
    timings = {"llm_extract_ms": 100.0, "llm_analyze_ms": 80.0}

    with patch("app.services.analyzer.create_pipeline") as mock_create:
        pipeline = MagicMock()
        pipeline.run = AsyncMock(return_value=(product, compatibility, usage, timings))
        mock_create.return_value = pipeline
        yield pipeline
