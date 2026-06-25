# Architecture — FitCheck

## Request flow

```
Browser (frontend)
    → POST /api/analyze { url, vehicle, debug? }
        → url_validator.validate_url (SSRF checks)
        → fetcher.fetch_page (Playwright Chromium)
        → extractor.extract_content (JSON-LD, Next data, OG, fitment DOM)
        → prefilter.prefilter_content (scored line truncation)
        → llm.pipeline.run
            → extract chain (product + fitment JSON)
            → [early exit if no fitment]
            → analyze chain (compatibility verdict)
        → AnalyzeResponse { product, compatibility, usage, timings }
```

## Components

| Layer | Responsibility |
|-------|----------------|
| `main.py` | FastAPI app, static files, exception handlers, lifespan browser cleanup |
| `routes/analyze.py` | Rate-limited analyze endpoint |
| `analyzer.py` | Pipeline orchestration and timing |
| `fetcher.py` | Playwright singleton, error mapping, bot diagnostics |
| `extractor.py` | Multi-source HTML parsing |
| `prefilter.py` | Token reduction before LLM |
| `llm/pipeline.py` | Two-stage chains with provider fallback |
| `frontend/` | Vanilla JS mobile UI with loading stages and error panels |

## Deployment

- **Local:** uvicorn on port 8000 with venv + `playwright install chromium`
- **Docker:** Single image, compose with `shm_size: 1gb`, healthcheck on `/api/health`
- **Production:** Reverse proxy (Caddy/Nginx) with HTTPS; API keys server-side only

## Observability

Responses include `timings` per stage and `usage` token counts per LLM stage. Debug mode adds fetch diagnostics (headers, body preview, bot vendor) on blocked fetches.
