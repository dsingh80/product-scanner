"""Heuristic prompt injection scanner.

Scans three surfaces before and after LLM calls:
  1. The vehicle description (direct injection by the user).
  2. Prefiltered page content (indirect injection via malicious product pages).
  3. LLM output fields post-parse (exfiltration / system-prompt leak markers).
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardResult:
    blocked: bool
    reason: str = ""
    matched_patterns: list[str] = field(default_factory=list)
    field_name: str = ""


# ---------------------------------------------------------------------------
# High-severity patterns — any single match triggers a block.
# These phrases essentially cannot appear in legitimate product or vehicle text.
# ---------------------------------------------------------------------------
_HIGH_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "ignore_instructions",
        re.compile(
            r"\bignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions?|prompts?|rules?|directives?)\b",
            re.I,
        ),
    ),
    (
        "disregard_instructions",
        re.compile(
            r"\bdisregard\s+(all\s+)?(previous|prior|above|system)\s+(instructions?|prompts?|rules?)\b",
            re.I,
        ),
    ),
    (
        "you_are_now",
        re.compile(r"\byou\s+are\s+now\s+(a|an|the)\b", re.I),
    ),
    (
        "reveal_system_prompt",
        re.compile(
            r"\b(reveal|expose|repeat|output|print)\s+(your\s+)?(system\s+)?(prompt|instructions?)\b",
            re.I,
        ),
    ),
    (
        "show_system_prompt",
        re.compile(
            r"\b(show|display)\s+(your\s+)?system\s+(prompt|instructions?)\b",
            re.I,
        ),
    ),
    (
        "override_safety",
        re.compile(
            r"\b(override|bypass|circumvent|unlock)\s+(your\s+)?(system|safety|restrictions?|guidelines?|rules?)\b",
            re.I,
        ),
    ),
    (
        "forget_instructions",
        re.compile(
            r"\b(forget|erase|clear|reset)\s+(all\s+)?(previous|prior|above)?\s*(instructions?|prompts?|context)\b",
            re.I,
        ),
    ),
    (
        "new_instructions_colon",
        re.compile(r"\bnew\s+instructions?\s*:", re.I),
    ),
    (
        "jailbreak_keyword",
        re.compile(r"\bjailbreak\b", re.I),
    ),
    (
        "system_xml_tag",
        re.compile(r"<\s*/?\s*system\s*>", re.I),
    ),
    (
        "llm_special_tokens",
        re.compile(r"\[INST\]|\[\/INST\]|<<SYS>>|<</SYS>>"),
    ),
    (
        "xml_delimiter_escape",
        re.compile(
            r"</\s*(untrusted_page_content|vehicle|fitment|product)\s*>.{0,200}(system|instruction)",
            re.I | re.S,
        ),
    ),
    (
        "bracket_system_command",
        re.compile(
            r"\[\s*(SYSTEM|ADMIN|OVERRIDE|INST|INSTRUCTION|PROMPT|CONTEXT)\s*:",
            re.I,
        ),
    ),
    (
        "brace_system_command",
        re.compile(
            r"\{\s*(system|admin|override|instruction|prompt)\s*:",
            re.I,
        ),
    ),
]

# ---------------------------------------------------------------------------
# Medium-severity patterns — require ≥2 matches to block.
# Individually these may appear in legitimate text; together they are suspicious.
# ---------------------------------------------------------------------------
_MEDIUM_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("developer_mode", re.compile(r"\bdeveloper\s+mode\b", re.I)),
    ("pretend_to_be", re.compile(r"\bpretend\s+(you\s+are|to\s+be)\b", re.I)),
    ("role_play_as", re.compile(r"\brole\s*-?\s*play\s+as\b", re.I)),
    ("act_as_ai", re.compile(r"\bact\s+as\s+(\w+\s+)*(AI|bot|assistant|language\s+model)\b", re.I)),
    ("no_restrictions", re.compile(r"\bno\s+restrictions\b", re.I)),
]

_MEDIUM_BLOCK_THRESHOLD = 2

# ---------------------------------------------------------------------------
# Output leak patterns — detect signs that the model disclosed its system
# prompt or was manipulated into meta-commentary about its instructions.
# ---------------------------------------------------------------------------
_OUTPUT_LEAK_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "system_prompt_leak",
        re.compile(r"you\s+are\s+a\s+product\s+data\s+extraction\s+assistant", re.I),
    ),
    (
        "instructions_leak",
        re.compile(r"\b(my\s+instructions?|i\s+was\s+told\s+to|i\s+am\s+programmed)\b", re.I),
    ),
    (
        "meta_commentary",
        re.compile(
            r"\b(as\s+an?\s+(AI|language\s+model)|i\s+(cannot|will\s+not|won't)\s+follow)\b",
            re.I,
        ),
    ),
]


def scan_text(text: str, field_name: str) -> GuardResult:
    """Scan a single text field for injection patterns."""
    if not text or not text.strip():
        return GuardResult(blocked=False, field_name=field_name)

    for name, pattern in _HIGH_PATTERNS:
        if pattern.search(text):
            return GuardResult(
                blocked=True,
                reason=f"High-severity injection pattern detected in {field_name!r}",
                matched_patterns=[name],
                field_name=field_name,
            )

    medium_hits: list[str] = []
    for name, pattern in _MEDIUM_PATTERNS:
        if pattern.search(text):
            medium_hits.append(name)

    if len(medium_hits) >= _MEDIUM_BLOCK_THRESHOLD:
        return GuardResult(
            blocked=True,
            reason=f"Multiple suspicious patterns detected in {field_name!r}",
            matched_patterns=medium_hits,
            field_name=field_name,
        )

    return GuardResult(blocked=False, matched_patterns=medium_hits, field_name=field_name)


def scan_vehicle(vehicle: str) -> GuardResult:
    """Scan the vehicle description for direct injection attempts."""
    return scan_text(vehicle, "vehicle")


def scan_page_content(content: str) -> GuardResult:
    """Scan prefiltered page content for indirect injection."""
    return scan_text(content, "page_content")


def scan_llm_output(output: dict[str, Any]) -> GuardResult:
    """Scan LLM output fields for prompt-leak / exfiltration markers."""
    fields_to_check = [
        ("summary", str(output.get("summary") or "")),
        ("notes", " ".join(str(n) for n in (output.get("notes") or []))),
        ("name", str(output.get("name") or "")),
        ("description", str(output.get("description") or "")),
    ]
    for field_name, text in fields_to_check:
        for pat_name, pattern in _OUTPUT_LEAK_PATTERNS:
            if pattern.search(text):
                return GuardResult(
                    blocked=True,
                    reason=f"LLM output leak pattern '{pat_name}' in field '{field_name}'",
                    matched_patterns=[pat_name],
                    field_name=f"output.{field_name}",
                )
    return GuardResult(blocked=False)
