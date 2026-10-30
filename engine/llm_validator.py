"""
LLM Validator — uses Gemini to check address quality and name validity.

Design decision: LLM is ONLY used for:
  1. Judging whether an address is complete and real
  2. Detecting fake/test names

It is NOT used for: scoring math, RTO rate calculation, feature weighting.
Reason: LLMs add latency and cost; simple code handles numeric logic better.

Falls back gracefully if Gemini API key is missing.
"""
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _get_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai as genai_new
        client = genai_new.Client(api_key=api_key)
        return ("new", client)
    except ImportError:
        pass
    try:
        import google.generativeai as genai_old  # type: ignore
        genai_old.configure(api_key=api_key)
        return ("old", genai_old.GenerativeModel("gemini-1.5-flash"))
    except ImportError:
        return None


def validate_order_with_llm(order: dict) -> dict:
    """
    Send one structured prompt to Gemini to assess:
      - address_score: 0-10 (0=clearly fake, 10=fully complete)
      - name_score: 0-10 (0=clearly fake, 10=genuine)
      - address_reason: short explanation
      - name_reason: short explanation

    Returns a dict with the above keys. Falls back to None values if LLM unavailable.
    """
    model = _get_model()
    if model is None:
        return {
            "address_score": None,
            "name_score": None,
            "address_reason": "LLM unavailable (no API key)",
            "name_reason": "LLM unavailable (no API key)",
        }

    address = order.get("address", "")
    name = order.get("customer_name", "")
    city = order.get("city", "")
    state = order.get("state", "")
    pincode = order.get("pincode", "")

    prompt = f"""You are reviewing an e-commerce order for a D2C brand in India.

Customer name: {name}
Address: {address}
City: {city}, {state} - {pincode}

Answer ONLY with a valid JSON object (no markdown, no explanation outside JSON):
{{
  "address_score": <integer 0-10>,
  "address_reason": "<one sentence in English>",
  "name_score": <integer 0-10>,
  "name_reason": "<one sentence in English>"
}}

Scoring guide:
- address_score 0-3: clearly fake/unusable (e.g., "xyz", ".", "call me", "near station", extremely vague)
- address_score 4-6: incomplete but possibly real (e.g., only a landmark, Hinglish direction only, no house number)
- address_score 7-10: complete and usable (has house/flat number, street/area/locality)

- name_score 0-3: clearly fake/test (e.g., "Test Order", "asdf", "xyz", "abc")
- name_score 4-6: unusual or single word, possibly real
- name_score 7-10: normal Indian name
"""

    try:
        sdk_type, model_obj = model
        if sdk_type == "new":
            resp = model_obj.models.generate_content(
                model="gemini-1.5-flash", contents=prompt
            )
            text = resp.text.strip()
        else:
            resp = model_obj.generate_content(prompt)
            text = resp.text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        return {
            "address_score": int(result.get("address_score", 5)),
            "name_score": int(result.get("name_score", 7)),
            "address_reason": result.get("address_reason", ""),
            "name_reason": result.get("name_reason", ""),
        }
    except Exception as e:
        return {
            "address_score": None,
            "name_score": None,
            "address_reason": f"LLM error: {e}",
            "name_reason": f"LLM error: {e}",
        }


def batch_validate(orders: list[dict], max_orders: int = None) -> list[dict]:
    """Validate a list of orders. Returns list of llm_score dicts."""
    results = []
    for i, order in enumerate(orders):
        if max_orders and i >= max_orders:
            results.append({"address_score": None, "name_score": None,
                            "address_reason": "skipped", "name_reason": "skipped"})
            continue
        results.append(validate_order_with_llm(order))
    return results
