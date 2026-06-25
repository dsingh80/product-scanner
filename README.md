# FitCheck — Vehicle Compatibility Scanner

A web application that scans e-commerce product pages and determines vehicle compatibility using Playwright page rendering and a two-stage LangChain LLM pipeline (Anthropic by default, OpenAI fallback).

## Features

- **SSRF-safe URL validation** — blocks localhost, private IPs, file://, and internal hostnames
- **Playwright Chromium fetcher** — renders SPAs (Next.js, Vue, etc.) before extraction
- **Structured content extraction** — JSON-LD, `__NEXT_DATA__`, OG tags, fitment blocks
- **Rule-based pre-filter** — reduces token usage before LLM calls
- **Two-stage LLM pipeline** — extract product/fitment data, then analyze compatibility (early exit when no fitment found)
- **Prompt injection defense** — heuristic scanner on vehicle input + page content + LLM output; hardened prompts with XML delimiters and defensive system instructions; LCEL-level guards in both chains
- **Mobile-first frontend** — paste URL + vehicle form with loading states and results
- **Browser capture mode** — bookmarklet or paste page text for eBay/Amazon when server fetch is blocked
- **Tiered rate limiting** — per-minute and per-hour caps per IP (proxy-header-aware); concurrency cap on LLM pipeline
- **Actionable error responses** — every error includes suggestions, a retryable flag, and a request ID for support correlation
- **Persistent structured logs** — JSON-lines via `RotatingFileHandler` to a Docker-mounted volume; stdout stream preserved for `docker compose logs`
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

## Docker (local)

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up --build -d
```

The app will be available at http://localhost:3001 (host port **3001** → container port **8000**).

> **Note:** Docker Compose sets `shm_size: 1gb` for Playwright stability.

## Deploy to a VPS

This app runs well on any small Linux VPS (1–2 GB RAM minimum recommended for Playwright). Docker is the simplest way to deploy.

### 1. Provision a server

Use any provider (DigitalOcean, Linode, Hetzner, AWS Lightsail, etc.):

- **OS:** Ubuntu 22.04 or 24.04 LTS
- **RAM:** 2 GB+ (Playwright + Chromium need headroom)
- **Ports:** open `22` (SSH) and `80`/`443` (HTTP/HTTPS)

### 2. Install Docker on the VPS

SSH into the server and run:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in so the docker group applies
```

### 3. Clone and configure

```bash
git clone https://github.com/YOUR_USER/product-scanner.git
cd product-scanner
cp .env.example .env
nano .env   # set ANTHROPIC_API_KEY and/or OPENAI_API_KEY
```

Recommended production `.env` values:

```env
LLM_PROVIDER=auto
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
RATE_LIMIT_PER_MINUTE=20
CORS_ORIGINS=https://yourdomain.com
PLAYWRIGHT_HEADLESS=true
```

### 4. Start the app

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:3001/api/health
```

The app listens on port **3001** on the host (mapped to 8000 inside the container). Do not expose 3001 publicly long-term — put a reverse proxy in front (next step).

### 5. Reverse proxy with HTTPS (Caddy — easiest)

Install [Caddy](https://caddyserver.com/docs/install) on the VPS:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Create `/etc/caddy/Caddyfile`:

```caddyfile
yourdomain.com {
    reverse_proxy localhost:3001
}
```

```bash
sudo systemctl reload caddy
```

Caddy obtains and renews Let's Encrypt certificates automatically. Your app is now at **https://yourdomain.com**.

#### Alternative: Nginx + Certbot

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/product-scanner`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # analyze requests can take 30–60s
        proxy_connect_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/product-scanner /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

### 6. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # or: sudo ufw allow 80,443/tcp
sudo ufw enable
```

Block direct access to port 3001 from the internet — only the reverse proxy should reach it.

### 7. Keep it running (auto-restart)

`docker-compose.yml` already sets `restart: unless-stopped`. After a reboot:

```bash
cd product-scanner
docker compose up -d
```

Optional: enable Docker at boot:

```bash
sudo systemctl enable docker
```

### 8. Updates

```bash
cd product-scanner
git pull
docker compose up --build -d
```

### 9. Access from your phone

Once HTTPS is configured, open **https://yourdomain.com** on any device. The UI is mobile-optimized — paste a product URL and enter your vehicle as free text.

### VPS checklist

| Step | Command / check |
|------|-----------------|
| Health | `curl https://yourdomain.com/api/health` |
| Logs (stream) | `docker compose logs -f` |
| Logs (file) | `tail -f logs/app.log \| jq .` |
| Disk | Image ~1.2 GB; ensure 10+ GB free |
| API keys | Never commit `.env`; keys stay server-side only |
| Rate limit | Tune `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR` for your usage |

### Production `.env` recommendations

```env
TRUST_PROXY_HEADERS=true         # required so rate limits use real client IPs
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=60
MAX_CONCURRENT_ANALYZE=2         # raise if your VPS has more than 2 GB RAM
LOG_DIR=/app/logs                # maps to ./logs on the host via the docker-compose volume
LOG_LEVEL=INFO
```

### Nginx — required headers for proxy-aware rate limiting

Add these lines to your `location /` block so `TRUST_PROXY_HEADERS=true` reads the real client IP:

```nginx
proxy_set_header X-Real-IP        $remote_addr;
proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;
```

Optional Nginx-level throttle as a first line of defence (add inside the `server {}` block):

```nginx
limit_req_zone $binary_remote_addr zone=fitcheck:10m rate=10r/m;
location /api/analyze {
    limit_req zone=fitcheck burst=3 nodelay;
    proxy_pass http://127.0.0.1:3001;
}
```

### Security

FitCheck uses defense-in-depth against prompt injection:

1. **Heuristic pre-scan** — blocks known jailbreak/instruction-override phrases in the vehicle field and prefiltered page content before any LLM call (zero token spend on blocked requests).
2. **LCEL chain guards** — `RunnableLambda` guards at the front of each LangChain chain re-check input fields at the chain level.
3. **Post-LLM output scan** — both extract and analyze results are scanned for system-prompt leakage markers before being returned.
4. **Hardened prompts** — defensive system instructions and XML delimiters in `prompts.py` separate untrusted data from model instructions (user-maintained, not auto-generated).

Every error response includes a `request_id` (also echoed as `X-Request-ID` header) for correlating errors across logs and user reports.

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

**Client-captured content** (bypasses server fetch — use for eBay, Amazon, etc.):

```json
{
  "vehicle": "2014 Peterbilt 386",
  "page_content": {
    "url": "https://www.ebay.com/itm/1234567890",
    "text": "…paste or bookmarklet-captured page text…",
    "html": "…optional full HTML…",
    "title": "Listing title",
    "json_ld": [],
    "source": "bookmarklet"
  }
}
```

When `DEBUG=true` in `.env`, fetch errors include a `fetch` object with the raw request (URL, headers) and response (status, headers, body preview, bot-protection detection). **No LLM calls are made if the page fetch fails.**

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
| `DEBUG` | `false` | Enable verbose fetch diagnostics on all analyze requests |
| `LLM_PROVIDER` | `auto` | `auto` (Anthropic → OpenAI fallback), `openai`, or `anthropic` |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `RATE_LIMIT_PER_MINUTE` | `10` | Per-IP request cap per minute on `/api/analyze` |
| `RATE_LIMIT_PER_HOUR` | `60` | Per-IP request cap per hour on `/api/analyze` |
| `TRUST_PROXY_HEADERS` | `false` | Set `true` when behind Nginx/Caddy so real client IPs are used for rate limiting |
| `MAX_CONCURRENT_ANALYZE` | `2` | Max simultaneous LLM pipeline invocations (excess requests get HTTP 503) |
| `FETCH_TIMEOUT_MS` | `30000` | Playwright page load timeout |
| `MAX_EXTRACT_CHARS` | `12000` | Max extracted text length |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `LOG_DIR` | `` | Directory for rotating log files (empty = stdout only) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_MAX_BYTES` | `10485760` | Max size per log file before rotation (default 10 MB) |
| `LOG_BACKUP_COUNT` | `10` | Number of rotated log files to keep (default ~100 MB total) |

### eBay / Amazon — use the bookmarklet

Server-side fetching often fails on eBay and Amazon (403 / bot checks), even with residential proxies. FitCheck can analyze content **captured in your own browser** instead:

1. Open FitCheck → **Bookmarklet** tab
2. Drag **Capture to FitCheck** to your bookmarks bar (mobile: copy the code into a bookmark URL)
3. Open the product listing on eBay or Amazon
4. Click the bookmark — FitCheck opens with the page text captured
5. Enter your vehicle and run the check

Alternatively, use **Paste page** mode: copy text from the listing and paste it in.

The API accepts `page_content` instead of `url`. Response `source` is `"client_content"` and `fetch_ms` is `0`.

### Debugging fetch failures (403 / bot blocks)

Many marketplaces (eBay, Amazon, etc.) return **HTTP 403** or a **200 OK challenge page** to headless browsers running on VPS/datacenter IPs.

Enable diagnostics by setting `DEBUG=true` in `.env`.

Error responses then include:

- `bot_protection` — detected vendor (Cloudflare, Incapsula, eBay, etc.)
- `suggestions` — actionable hints (including bookmarklet guidance for eBay/Amazon)
- `fetch` (when `DEBUG=true`) — structured `request` + `response` trace: URL, headers, status, body preview, visible text preview, bot protection

Example error shape:

```json
{
  "error": {
    "code": "FETCH_BLOCKED",
    "message": "eBay bot check blocked automated access (HTTP 403)",
    "details": {
      "status_code": 403,
      "final_url": "https://www.ebay.com/itm/...",
      "bot_protection": { "detected": true, "vendor": "ebay", "vendor_name": "eBay bot check" },
      "suggestions": ["..."],
      "fetch": {
        "request": { "method": "GET", "url": "..." },
        "response": { "status": 403, "body_preview": "...", "visible_text_preview": "..." }
      }
    }
  }
}
```

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
