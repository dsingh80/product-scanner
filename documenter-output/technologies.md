# Technologies — FitCheck

## FastAPI

**Role in project:** Hosts REST API, serves static frontend, registers CORS/rate-limit middleware, centralizes AppError handling.

**Typical purpose:** Async Python web framework for typed HTTP APIs.

**Advantages over alternatives:** Native async fits Playwright and LangChain; OpenAPI + Pydantic validation without Flask/Django boilerplate.

## Playwright

**Role in project:** Headless Chromium renders product pages including SPAs; singleton browser with lifespan cleanup.

**Typical purpose:** Browser automation for reliable page rendering.

**Advantages over alternatives:** Executes JavaScript for Next.js/Vue storefronts; response inspection for bot-block diagnostics.

## LangChain

**Role in project:** LCEL chains for extract and analyze stages; cached per provider.

**Typical purpose:** Composable LLM application framework.

**Advantages over alternatives:** Swappable provider adapters without rewriting orchestration.

## Anthropic Claude / OpenAI GPT

**Role in project:** Primary (Haiku) and fallback (gpt-4o-mini) providers with automatic failover on quota/rate-limit errors.

**Typical purpose:** Cloud LLMs for structured extraction and reasoning.

**Advantages over alternatives:** Auto mode improves availability without user provider selection.

## Pydantic

**Role in project:** API models, Settings from .env, typed configuration singleton.

**Typical purpose:** Data validation and settings for Python apps.

**Advantages over alternatives:** FastAPI-native; pydantic-settings for environment loading.

## BeautifulSoup4

**Role in project:** Parses HTML for JSON-LD, __NEXT_DATA__, OG/meta, fitment DOM blocks.

**Typical purpose:** HTML parsing for web content extraction.

**Advantages over alternatives:** Handles heterogeneous e-commerce structures without per-site scrapers.

## slowapi

**Role in project:** Per-IP rate limiting on analyze endpoint (default 10/min).

**Typical purpose:** Rate limiting for Starlette/FastAPI.

**Advantages over alternatives:** Protects expensive pipeline without Redis for single-node deploys.

## Docker

**Role in project:** Single image with Chromium, backend, frontend; compose shm_size for stability.

**Typical purpose:** Containerized packaging and VPS deployment.

**Advantages over alternatives:** Reproduces Playwright deps without manual system packages.

## pytest

**Role in project:** Unit, integration, and smoke tests with async and mock support.

**Typical purpose:** Python testing framework.

**Advantages over alternatives:** pytest-asyncio and pytest-mock for async routes and mocked dependencies.
