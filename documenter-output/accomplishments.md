# Accomplishments — FitCheck

## SPA-aware vehicle compatibility scanner

**Technologies:** FastAPI, Playwright, LangChain

End-to-end web app accepting product URL + vehicle description, rendering pages in Chromium, extracting fitment signals, and returning structured compatibility analysis. Handles JS storefronts with chained LLM stages and early exit instead of regex-only parsers.

## Token-efficient LLM fitment analysis

**Technologies:** LangChain, BeautifulSoup4

Multi-source HTML extraction, rule-based prefilter scoring, and conditional second-stage analyze minimize tokens per scan. Skips analyze when no fitment exists.

## Marketplace bot-block diagnostics

**Technologies:** Playwright, FastAPI

Fetch layer detects vendor-specific bot protection and returns structured suggestions plus optional debug headers/body preview. Supports UI and API debug mode for VPS marketplace blocks.
