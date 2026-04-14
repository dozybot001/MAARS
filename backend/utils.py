"""Shared utilities for the MAARS backend."""

import json
import re


def parse_json_fenced(text: str, fallback: dict | None = None) -> dict:
    """Extract a JSON object from LLM output that may be wrapped in markdown fences.

    Tries raw JSON first, then looks for ```json ... ``` blocks.
    Returns *fallback* (default empty dict) on parse failure.
    """
    _fallback = fallback if fallback is not None else {}
    text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    return _fallback
