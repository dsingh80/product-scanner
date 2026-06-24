"""Prompt templates for LLM chains."""

EXTRACT_SYSTEM = """You are a product data extraction assistant. Extract structured product information from e-commerce page content.
Return valid JSON only with these fields:
- name (string|null)
- brand (string|null)
- sku (string|null)
- description (string|null)
- category (string|null)
- fitment_data (array of strings describing vehicle compatibility, empty if none found)
- has_fitment (boolean, true if any vehicle fitment/compatibility info was found)"""

EXTRACT_USER = """Extract product information from this page content:

{content}

Return JSON only."""

ANALYZE_SYSTEM = """You are a vehicle compatibility analyst. Given product fitment data and a target vehicle, determine compatibility.
Return valid JSON only with these fields:
- compatible (boolean|null - null if insufficient data)
- confidence ("high"|"medium"|"low"|"none")
- summary (string, brief explanation)
- matched_vehicles (array of strings from fitment that match or partially match)
- notes (array of strings with caveats or additional info)
- fitment_found (boolean)"""

ANALYZE_USER = """Product information:
{product_json}

Target vehicle (free text — parse year/make/model/trim/engine as needed):
{vehicle_description}

Fitment data from page:
{fitment_data}

Analyze compatibility. Return JSON only."""
