"""Site-specific extraction hints and fetch-failure guidance."""

import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

EBAY_ITEM_RE = re.compile(r"ebay\.com/(?:itm|p)/(?:[^/?#]+/)?(\d{10,})", re.I)
AMAZON_ASIN_RE = re.compile(r"amazon\.com/(?:dp|gp/product)/([A-Z0-9]{10})", re.I)


def detect_site(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    if "ebay." in host:
        return "ebay"
    if "amazon." in host:
        return "amazon"
    return None


def extract_site_id(url: str | None) -> dict[str, str]:
    if not url:
        return {}
    site = detect_site(url)
    if site == "ebay":
        m = EBAY_ITEM_RE.search(url)
        if m:
            return {"site": "ebay", "item_id": m.group(1)}
    if site == "amazon":
        m = AMAZON_ASIN_RE.search(url)
        if m:
            return {"site": "amazon", "asin": m.group(1)}
    return {"site": site} if site else {}


def enrich_site_extraction(soup: BeautifulSoup, source_url: str, structured: dict[str, Any]) -> dict[str, Any]:
    site = detect_site(source_url)
    extra_blocks: list[str] = list(structured.get("fitment_blocks") or [])

    if site == "ebay":
        extra_blocks.extend(_ebay_blocks(soup))
    elif site == "amazon":
        extra_blocks.extend(_amazon_blocks(soup))

    if extra_blocks:
        seen = set(structured.get("fitment_blocks") or [])
        merged = list(structured.get("fitment_blocks") or [])
        for block in extra_blocks:
            if block not in seen:
                seen.add(block)
                merged.append(block)
        structured["fitment_blocks"] = merged
        structured["site"] = site

    return structured


def _ebay_blocks(soup: BeautifulSoup) -> list[str]:
    blocks: list[str] = []
    selectors = [
        ".x-item-specifics",
        "#vi-desc-maincntr",
        "[data-testid='x-item-specifics']",
        ".ux-layout-section--itemSpecs",
        ".ux-labels-values",
        "#UserField0",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            text = " ".join(el.get_text(separator=" ", strip=True).split())
            if len(text) > 15:
                blocks.append(f"EBAY:{text[:4000]}")
    return blocks


def _amazon_blocks(soup: BeautifulSoup) -> list[str]:
    blocks: list[str] = []
    for el in soup.select("#productDetails_db_sections, #detailBullets_feature_div, #fitmentDiv"):
        text = " ".join(el.get_text(separator=" ", strip=True).split())
        if len(text) > 15:
            blocks.append(f"AMAZON:{text[:4000]}")
    return blocks


def blocked_site_suggestions(url: str | None) -> list[str]:
    site = detect_site(url)
    if site == "ebay":
        return [
            "eBay blocks server-side fetching. Use the FitCheck bookmarklet while viewing the listing in your browser.",
            "Open the eBay item on your phone, run the bookmarklet, then check compatibility here.",
        ]
    if site == "amazon":
        return [
            "Amazon blocks automated fetching. Use the bookmarklet on the product page or paste the item description.",
        ]
    return [
        "This site may block server fetches. Try the bookmarklet on the product page in your browser.",
    ]
