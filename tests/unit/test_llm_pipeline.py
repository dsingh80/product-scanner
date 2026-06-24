"""Unit tests for LLM pipeline (mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.errors import AppError, ErrorCode
from app.services.llm.pipeline import LLMPipeline


@pytest.fixture
def vehicle():
    return "2020 Toyota Camry SE"


class TestLLMPipeline:
    @pytest.mark.asyncio
    async def test_early_exit_no_fitment(self, vehicle):
        settings = Settings(openai_api_key="test-key", llm_provider="openai")
        pipeline = LLMPipeline(settings)

        mock_extract_chain = MagicMock()
        mock_extract_chain.ainvoke = AsyncMock(return_value={
            "name": "Widget",
            "brand": "Acme",
            "sku": None,
            "description": "A widget",
            "category": "Parts",
            "fitment_data": [],
            "has_fitment": False,
        })
        mock_analyze_chain = MagicMock()
        mock_analyze_chain.ainvoke = AsyncMock()

        pipeline._chains[("openai", "extract")] = mock_extract_chain
        pipeline._chains[("openai", "analyze")] = mock_analyze_chain

        product, compatibility, usage, timings = await pipeline.run(
            "Some product content", vehicle, "https://example.com"
        )

        assert product.name == "Widget"
        assert compatibility.fitment_found is False
        assert compatibility.confidence == "none"
        mock_analyze_chain.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_pipeline_with_fitment(self, vehicle):
        settings = Settings(openai_api_key="test-key", llm_provider="openai")
        pipeline = LLMPipeline(settings)

        mock_extract_chain = MagicMock()
        mock_extract_chain.ainvoke = AsyncMock(return_value={
            "name": "Brake Pads",
            "brand": "StopTech",
            "sku": "ST-1234",
            "description": "Ceramic pads",
            "category": "Brakes",
            "fitment_data": ["2020 Toyota Camry SE"],
            "has_fitment": True,
        })
        mock_analyze_chain = MagicMock()
        mock_analyze_chain.ainvoke = AsyncMock(return_value={
            "compatible": True,
            "confidence": "high",
            "summary": "Direct fit for your vehicle.",
            "matched_vehicles": ["2020 Toyota Camry SE"],
            "notes": [],
            "fitment_found": True,
        })

        pipeline._chains[("openai", "extract")] = mock_extract_chain
        pipeline._chains[("openai", "analyze")] = mock_analyze_chain

        product, compatibility, usage, timings = await pipeline.run(
            "Fitment: 2020 Toyota Camry SE", vehicle, "https://example.com"
        )

        assert product.name == "Brake Pads"
        assert compatibility.compatible is True
        assert compatibility.confidence == "high"
        mock_analyze_chain.ainvoke.assert_called_once()
        assert "llm_extract_ms" in timings
        assert "llm_analyze_ms" in timings

    @pytest.mark.asyncio
    async def test_fallback_to_openai_on_anthropic_quota(self, vehicle):
        settings = Settings(
            llm_provider="auto",
            anthropic_api_key="ant-key",
            openai_api_key="oai-key",
        )
        pipeline = LLMPipeline(settings)

        mock_anthropic_extract = MagicMock()
        mock_anthropic_extract.ainvoke = AsyncMock(
            side_effect=RuntimeError("Error code: 429 - insufficient_quota")
        )
        mock_openai_extract = MagicMock()
        mock_openai_extract.ainvoke = AsyncMock(return_value={
            "name": "Brake Pads",
            "brand": "StopTech",
            "sku": "ST-1234",
            "description": "Ceramic pads",
            "category": "Brakes",
            "fitment_data": [],
            "has_fitment": False,
        })

        pipeline._chains[("anthropic", "extract")] = mock_anthropic_extract
        pipeline._chains[("openai", "extract")] = mock_openai_extract

        product, compatibility, usage, timings = await pipeline.run(
            "Some product content", vehicle, "https://example.com"
        )

        assert product.name == "Brake Pads"
        mock_anthropic_extract.ainvoke.assert_awaited_once()
        mock_openai_extract.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_not_configured(self):
        settings = Settings(
            openai_api_key="",
            anthropic_api_key="",
            llm_provider="auto",
        )
        pipeline = LLMPipeline(settings)
        vehicle = "2020 Toyota Camry"

        with pytest.raises(AppError) as exc:
            await pipeline.run("content", vehicle, "https://example.com")
        assert exc.value.code == ErrorCode.LLM_NOT_CONFIGURED
