"""Integration tests for API endpoints."""

from unittest.mock import AsyncMock, patch


class TestHealthEndpoint:
    def test_health_returns_status(self, client):
        with patch(
            "app.routes.analyze.check_playwright_health",
            new_callable=AsyncMock,
            return_value={"status": "ok", "browser_connected": True},
        ):
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "playwright" in data
            assert "llm" in data


class TestAnalyzeEndpoint:
    def test_analyze_success(self, client, mock_fetch, mock_llm_pipeline):
        payload = {
            "url": "https://example.com/product/brake-pads",
            "vehicle": "2020 Toyota Camry SE",
        }
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["product"]["name"] == "Ceramic Brake Pads"
        assert data["compatibility"]["compatible"] is True
        assert "usage" in data
        assert "timings" in data
        assert "validate_ms" in data["timings"]
        assert "fetch_ms" in data["timings"]
        assert "extract_ms" in data["timings"]
        assert "prefilter_ms" in data["timings"]
        assert "llm_extract_ms" in data["timings"]
        assert "llm_analyze_ms" in data["timings"]
        assert "total_ms" in data["timings"]

    def test_analyze_blocks_localhost(self, client):
        payload = {
            "url": "http://localhost/product",
            "vehicle": "2020 Toyota Camry",
        }
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "URL_BLOCKED_LOCALHOST"

    def test_analyze_invalid_payload(self, client):
        response = client.post("/api/analyze", json={"url": "not-valid"})
        assert response.status_code == 422


class TestCORS:
    def test_cors_headers_on_options(self, client):
        response = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_headers_on_response(self, client, mock_fetch, mock_llm_pipeline):
        payload = {
            "url": "https://example.com/product",
            "vehicle": "2020 Toyota Camry",
        }
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in response.headers
