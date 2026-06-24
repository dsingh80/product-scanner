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

    def test_analyze_client_content_skips_fetch(self, client, mock_llm_pipeline):
        with patch("app.services.analyzer.fetch_page", new_callable=AsyncMock) as mock_fetch:
            payload = {
                "vehicle": "2014 Peterbilt 386",
                "page_content": {
                    "url": "https://www.ebay.com/itm/1234567890",
                    "text": "Fits 2014 Peterbilt 386. EBP sensor for Cummins ISX.",
                    "source": "paste",
                },
            }
            response = client.post("/api/analyze", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "client_content"
            assert data["timings"]["fetch_ms"] == 0
            mock_fetch.assert_not_called()
            mock_llm_pipeline.run.assert_called_once()

    def test_analyze_fetch_failure_skips_llm(self, client):
        from app.errors import AppError, ErrorCode

        fetch_error = AppError(
            ErrorCode.FETCH_BLOCKED,
            "Blocked by bot protection",
            status_code=502,
            details={
                "status_code": 403,
                "fetch": {"request": {"url": "https://www.ebay.com/itm/1"}, "response": {"status": 403}},
            },
        )
        with patch("app.services.analyzer.fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = fetch_error
            with patch("app.services.analyzer.create_pipeline") as mock_create:
                response = client.post(
                    "/api/analyze",
                    json={
                        "url": "https://www.ebay.com/itm/1234567890",
                        "vehicle": "2014 Peterbilt 386",
                    },
                )
                assert response.status_code == 502
                data = response.json()
                assert data["error"]["code"] == "FETCH_BLOCKED"
                assert "fetch" in data["error"]["details"]
                mock_create.assert_not_called()


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
