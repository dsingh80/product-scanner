# Product Vehicle Compatibility Scanner

A web application that scans e-commerce product pages and determines vehicle compatibility using Playwright page rendering and a two-stage LangChain LLM pipeline.

## Features

- **SSRF-safe URL validation** — blocks localhost, private IPs, file://, and internal hostnames
- **Playwright Chromium fetcher** — renders SPAs (Next.js, Vue, etc.) before extraction
- **Structured content extraction** — JSON-LD, `__NEXT_DATA__`, OG tags, fitment blocks
- **Rule-based pre-filter** — reduces token usage before LLM calls
- **Two-stage LLM pipeline** — extract product/fitment data, then analyze compatibility (early exit when no fitment found)
- **Mobile-first frontend** — paste URL + vehicle form with loading states and results
- **Rate limiting** — 10 requests/minute per IP (configurable)
- **Docker support** — single image with Playwright Chromium

## Quick Start (Local)

### Prerequisites

- Python 3.12+
- Playwright Chromium (installed via pip)

### Setup

```bash
# Clone and enter project
cd product-scanner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY or ANTHROPIC_API_KEY

# Run server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Run Tests

```bash
pip install -r backend/requirements.txt
pytest tests/ -v
```

### Smoke Test

With the server running:

```bash
python tests/scripts/smoke_test.py
```

## Docker

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up --build
```

The app will be available at http://localhost:8000.

> **Note:** Docker Compose sets `shm_size: 1gb` for Playwright stability.

## API

### `GET /api/health`

Returns Playwright and LLM configuration status.

### `POST /api/analyze`

```json
{
  "url": "https://example.com/product/brake-pads",
  "vehicle": "2020 Toyota Camry SE"
}
```

Response includes `product`, `compatibility`, `usage` (per-stage token counts), and `timings`:

```json
{
  "product": { "name": "...", "brand": "...", "sku": "..." },
  "compatibility": {
    "compatible": true,
    "confidence": "high",
    "summary": "...",
    "matched_vehicles": ["..."],
    "notes": ["..."],
    "fitment_found": true
  },
  "usage": {
    "extract": { "input_tokens": 100, "output_tokens": 50, "total_tokens": 150 },
    "analyze": { "input_tokens": 80, "output_tokens": 40, "total_tokens": 120 }
  },
  "timings": {
    "validate_ms": 1.2,
    "fetch_ms": 3500.0,
    "extract_ms": 15.0,
    "prefilter_ms": 2.0,
    "llm_extract_ms": 800.0,
    "llm_analyze_ms": 600.0,
    "total_ms": 4918.2
  }
}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `RATE_LIMIT_PER_MINUTE` | `10` | API rate limit per IP |
| `FETCH_TIMEOUT_MS` | `30000` | Playwright page load timeout |
| `MAX_EXTRACT_CHARS` | `12000` | Max extracted text length |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## Project Structure

```
product-scanner/
├── backend/app/          # FastAPI application
│   ├── main.py           # App entry point
│   ├── config.py         # Settings
│   ├── models.py         # Pydantic models
│   ├── errors.py         # Error codes
│   ├── routes/           # API routes
│   ├── middleware/       # Rate limit, CORS
│   └── services/         # Core logic
│       ├── url_validator.py
│       ├── fetcher.py
│       ├── extractor.py
│       ├── prefilter.py
│       ├── analyzer.py
│       └── llm/          # LangChain pipeline
├── frontend/             # Static UI
├── tests/                # pytest suite
└── Dockerfile
```

## License

MIT
