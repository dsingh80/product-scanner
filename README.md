# FitCheck — Vehicle Compatibility Scanner

A web application that scans e-commerce product pages and determines vehicle compatibility using Playwright page rendering and a two-stage LangChain LLM pipeline (Anthropic by default, OpenAI fallback).

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

## Docker (local)

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up --build -d
```

The app will be available at http://localhost:8000.

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
curl http://localhost:8000/api/health
```

The app listens on port **8000** inside the server. Do not expose 8000 publicly long-term — put a reverse proxy in front (next step).

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
    reverse_proxy localhost:8000
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
        proxy_pass http://127.0.0.1:8000;
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

Block direct access to port 8000 from the internet — only the reverse proxy should reach it.

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
| Logs | `docker compose logs -f` |
| Disk | Image ~1.2 GB; ensure 10+ GB free |
| API keys | Never commit `.env`; keys stay server-side only |
| Rate limit | Tune `RATE_LIMIT_PER_MINUTE` for your usage |

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
| `LLM_PROVIDER` | `auto` | `auto` (Anthropic → OpenAI fallback), `openai`, or `anthropic` |
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
