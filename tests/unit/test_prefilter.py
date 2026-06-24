"""Unit tests for prefilter."""

from app.services.extractor import extract_content
from app.services.prefilter import prefilter_content


class TestPrefilter:
    def test_keeps_fitment_lines(self):
        html = """
        <html><body>
        <div class="fitment">Fits 2020 Toyota Camry SE 2.5L engine</div>
        <div>Subscribe to newsletter for free shipping deals</div>
        </body></html>
        """
        extracted = extract_content(html, "https://example.com")
        filtered = prefilter_content(extracted)
        assert "Toyota Camry" in filtered
        assert "newsletter" not in filtered.lower() or "Toyota" in filtered

    def test_returns_content_when_all_scored_low(self):
        extracted = {"combined_text": "Short text about a product."}
        result = prefilter_content(extracted, max_chars=1000)
        assert "product" in result

    def test_respects_max_chars(self):
        lines = "\n".join(f"Fits 2020 Toyota Camry line {i}" for i in range(100))
        extracted = {"combined_text": lines}
        result = prefilter_content(extracted, max_chars=200)
        assert len(result) <= 200
