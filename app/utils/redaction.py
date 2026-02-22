from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\-\s().]{7,}\d)(?!\w)")
MONEY_KEYS = {"salary", "bonus", "equity", "amount", "comp", "cash"}


def _bucket_number(value: float) -> str:
    if value < 50_000:
        return "<50k"
    if value < 100_000:
        return "50k-100k"
    if value < 200_000:
        return "100k-200k"
    if value < 300_000:
        return "200k-300k"
    return "300k+"


def redact_pii_strings(text: str) -> str:
    scrubbed = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    scrubbed = PHONE_RE.sub("[REDACTED_PHONE]", scrubbed)
    return scrubbed[:200]


def redact_money_values(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            key_lower = key.lower()
            if any(token in key_lower for token in MONEY_KEYS) and isinstance(value, (int, float)):
                out[key] = _bucket_number(float(value))
            else:
                out[key] = redact_money_values(value)
        return out
    if isinstance(obj, list):
        return [redact_money_values(item) for item in obj]
    if isinstance(obj, str):
        return redact_pii_strings(obj)
    return obj
