"""Stage 2: Analyze vehicle compatibility."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from app.services.llm.prompts import ANALYZE_SYSTEM, ANALYZE_USER


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        return {
            "compatible": None,
            "confidence": "none",
            "summary": "Unable to parse compatibility analysis",
            "matched_vehicles": [],
            "notes": [],
            "fitment_found": False,
        }


def build_analyze_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYZE_SYSTEM),
        ("human", ANALYZE_USER),
    ])
    return prompt | llm | StrOutputParser() | RunnableLambda(_parse_json)
