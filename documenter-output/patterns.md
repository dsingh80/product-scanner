# Patterns — FitCheck

## Two-stage LLM pipeline with early exit

Skips the analyze LLM call when extract finds no fitment data, returning immediately with a no-fitment result. Reduces token cost and latency on incompatible pages.

## SSRF-safe URL validation

Blocks localhost, private IPs, file://, internal hostnames, and DNS-rebound private addresses before fetch. Defense in depth for user-supplied URLs.

## Structured multi-source content extraction

Merges JSON-LD, Next.js __NEXT_DATA__, OG tags, meta, and fitment DOM selectors into combined text. Works across retailers without site-specific modules.

## Rule-based LLM prefilter

Scores lines by fitment keywords and penalizes noise (cookies, social, shipping). Truncates to high-signal text within char budget without an extra LLM call.

## LLM provider fallback

Anthropic-first with OpenAI retry on quota/rate-limit markers. Improves uptime when a second API key is configured.

## Bot protection diagnostics

Detects Cloudflare, eBay, Amazon, and CAPTCHA interstitials; returns vendor, suggestions, and optional debug payload on fetch failures.

## Pipeline orchestration service

`analyze_product` sequences validate → fetch → extract → prefilter → LLM with per-stage timings. Keeps routes thin and stages independently testable.

## Typed application error taxonomy

`AppError` + `ErrorCode` enum produce consistent JSON errors for URL, fetch, extract, and LLM failures consumed by the frontend.
