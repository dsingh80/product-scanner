"""Stage 1: Extract product and fitment data from page content."""

import json
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from app.services.llm.prompts import EXTRACT_SYSTEM, EXTRACT_USER


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
            "name": None,
            "brand": None,
            "sku": None,
            "description": None,
            "category": None,
            "fitment_data": [],
            "has_fitment": False,
        }


def build_extract_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACT_SYSTEM),
        ("human", EXTRACT_USER),
    ])
    return prompt | llm | StrOutputParser() | RunnableLambda(_parse_json)
