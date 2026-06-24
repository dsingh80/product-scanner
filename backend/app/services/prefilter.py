"""Rule-based token reduction before LLM processing."""

import re
from typing import Any

NOISE_PATTERNS = [
    re.compile(r"\b(cookie|privacy|newsletter|subscribe|sign up|cart|checkout)\b", re.I),
    re.compile(r"\b(facebook|twitter|instagram|pinterest|youtube)\b", re.I),
    re.compile(r"\b(free shipping|return policy|warranty)\b", re.I),
]

FITMENT_PATTERNS = [
    re.compile(r"\b(\d{4})\s+([A-Za-z]+)\s+([A-Za-z0-9\-]+)", re.I),
    re.compile(r"\bfits?\b", re.I),
    re.compile(r"\bcompatible\b", re.I),
    re.compile(r"\bfitment\b", re.I),
    re.compile(r"\bvehicle\b", re.I),
    re.compile(r"\bapplication\b", re.I),
    re.compile(r"\bengine\b", re.I),
    re.compile(r"\btrim\b", re.I),
]


def _score_line(line: str) -> int:
    score = 0
    for pat in FITMENT_PATTERNS:
        if pat.search(line):
            score += 2
    for pat in NOISE_PATTERNS:
        if pat.search(line):
            score -= 3
    if len(line) > 20:
        score += 1
    return score


def prefilter_content(extracted: dict[str, Any], max_chars: int = 8000) -> str:
    """Reduce extracted content to high-signal text for LLM."""
    combined = extracted.get("combined_text", "")
    if not combined:
        return ""

    lines = [ln.strip() for ln in combined.split("\n") if ln.strip()]
    scored = sorted((( _score_line(ln), ln) for ln in lines), key=lambda x: x[0], reverse=True)

    result_lines: list[str] = []
    total = 0
    for score, line in scored:
        if score < 0:
            continue
        if total + len(line) + 1 > max_chars:
            remaining = max_chars - total - 1
            if remaining > 50:
                result_lines.append(line[:remaining])
            break
        result_lines.append(line)
        total += len(line) + 1

    if not result_lines:
        return combined[:max_chars]

    return "\n".join(result_lines)
