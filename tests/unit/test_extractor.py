"""Unit tests for HTML extractor."""

from pathlib import Path

from app.services.extractor import extract_content

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "pages"


class TestExtractor:
    def test_extracts_json_ld(self):
        html = (FIXTURES / "product_with_fitment.html").read_text(encoding="utf-8")
        result = extract_content(html, "https://example.com/product")
        assert result["json_ld"]
        assert any("Ceramic Brake Pads" in str(item) for item in result["json_ld"])

    def test_extracts_meta_and_og(self):
        html = (FIXTURES / "product_with_fitment.html").read_text(encoding="utf-8")
        result = extract_content(html, "https://example.com/product")
        assert result["meta"]["title"] == "Ceramic Brake Pads - StopTech"
        assert "og:title" in result["og_tags"]

    def test_extracts_fitment_blocks(self):
        html = (FIXTURES / "product_with_fitment.html").read_text(encoding="utf-8")
        result = extract_content(html, "https://example.com/product")
        assert result["fitment_blocks"]
        assert result["has_fitment_hints"] is True

    def test_no_fitment_page(self):
        html = (FIXTURES / "product_no_fitment.html").read_text(encoding="utf-8")
        result = extract_content(html, "https://example.com/widget")
        assert not result["fitment_blocks"]
        assert result["has_fitment_hints"] is False

    def test_combined_text_capped(self, monkeypatch):
        monkeypatch.setenv("MAX_EXTRACT_CHARS", "500")
        from app.config import get_settings

        get_settings.cache_clear()
        html = (FIXTURES / "product_with_fitment.html").read_text(encoding="utf-8")
        result = extract_content(html, "https://example.com/product")
        assert len(result["combined_text"]) <= 500
        get_settings.cache_clear()
