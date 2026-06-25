# Project Overview — FitCheck

**Slug:** `product-scanner`  
**Domain:** E-commerce vehicle fitment / compatibility checking

## Purpose

FitCheck is a web application that scans e-commerce product pages and determines whether a product is compatible with a user-specified vehicle. Users paste a product URL and enter vehicle details (e.g. "2020 Toyota Camry SE"); the backend fetches and renders the page, extracts fitment-related content, and runs a two-stage LLM pipeline to return structured compatibility results.

## Layout

```
product-scanner/
├── backend/app/          # FastAPI application
│   ├── main.py           # App entry, static frontend, middleware
│   ├── config.py         # pydantic-settings from .env
│   ├── models.py         # Request/response models
│   ├── errors.py         # AppError taxonomy
│   ├── routes/           # /api/analyze, /api/health
│   ├── middleware/       # CORS, rate limiting
│   └── services/         # Core pipeline
│       ├── url_validator.py
│       ├── fetcher.py
│       ├── extractor.py
│       ├── prefilter.py
│       ├── analyzer.py
│       ├── fetch_diagnostics.py
│       └── llm/          # LangChain chains and pipeline
├── frontend/             # Mobile-first static UI
├── tests/                # pytest unit, integration, smoke
├── Dockerfile
└── docker-compose.yml
```

## Key capabilities

- SSRF-safe URL validation before fetch
- Playwright Chromium rendering for SPAs
- Structured extraction from JSON-LD, Next.js data, OG tags, fitment blocks
- Rule-based prefilter to reduce LLM tokens
- Two-stage LLM extract → analyze with early exit
- Anthropic/OpenAI provider fallback
- Bot protection diagnostics for marketplace blocks
- Docker deployment with health checks
