"""HTML content extraction for product and fitment data."""

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from app.config import get_settings

FITMENT_KEYWORDS = re.compile(
    r"\b(fits?|compatible|fitment|vehicle|year|make|model|trim|engine|application)\b",
    re.I,
)


def _extract_json_ld(soup: BeautifulSoup) -> list[Any]:
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def _extract_next_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return None


def _extract_og_tags(soup: BeautifulSoup) -> dict[str, str]:
    og: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name") or ""
        if prop.startswith("og:") or prop in ("description", "keywords"):
            content = meta.get("content")
            if content:
                og[prop] = content.strip()
    return og


def _extract_meta(soup: BeautifulSoup) -> dict[str, str]:
    meta: dict[str, str] = {}
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        meta["title"] = title_tag.string.strip()
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        meta["description"] = desc["content"].strip()
    return meta


def _extract_fitment_blocks(soup: BeautifulSoup) -> list[str]:
    blocks: list[str] = []
    selectors = [
        "[class*='fitment']",
        "[class*='compatibility']",
        "[class*='vehicle']",
        "[id*='fitment']",
        "[id*='compatibility']",
        "[data-fitment]",
        "table",
    ]
    seen: set[str] = set()
    for selector in selectors:
        for el in soup.select(selector):
            text = " ".join(el.get_text(separator=" ", strip=True).split())
            if len(text) < 20 or not FITMENT_KEYWORDS.search(text):
                continue
            if text not in seen:
                seen.add(text)
                blocks.append(text)
    return blocks


def _extract_body_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    body = soup.find("body")
    if not body:
        return ""
    text = " ".join(body.get_text(separator=" ", strip=True).split())
    return text


def _cap_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def extract_content(html: str, source_url: str) -> dict[str, Any]:
    """Extract structured content from HTML, capped at max_extract_chars."""
    settings = get_settings()
    soup = BeautifulSoup(html, "lxml")

    json_ld = _extract_json_ld(soup)
    next_data = _extract_next_data(soup)
    og_tags = _extract_og_tags(soup)
    meta = _extract_meta(soup)
    fitment_blocks = _extract_fitment_blocks(soup)
    body_text = _extract_body_text(soup)

    structured = {
        "source_url": source_url,
        "json_ld": json_ld,
        "next_data": next_data,
        "og_tags": og_tags,
        "meta": meta,
        "fitment_blocks": fitment_blocks,
        "body_text": body_text,
    }

    parts: list[str] = []
    if meta.get("title"):
        parts.append(f"TITLE: {meta['title']}")
    if meta.get("description"):
        parts.append(f"DESCRIPTION: {meta['description']}")
    if og_tags:
        parts.append("OG: " + json.dumps(og_tags, ensure_ascii=False))
    if json_ld:
        parts.append("JSON-LD: " + json.dumps(json_ld, ensure_ascii=False))
    if next_data:
        parts.append("NEXT_DATA: " + json.dumps(next_data, ensure_ascii=False))
    if fitment_blocks:
        parts.append("FITMENT: " + "\n---\n".join(fitment_blocks))
    if body_text:
        parts.append("BODY: " + body_text)

    combined = "\n\n".join(parts)
    structured["combined_text"] = _cap_text(combined, settings.max_extract_chars)
    structured["has_fitment_hints"] = bool(fitment_blocks) or bool(
        re.search(
            r"\b(fits?\s+\d{4}|compatible with|fitment:|vehicle fitment|application[s]?:)\b",
            combined,
            re.I,
        )
    )
    return structured
