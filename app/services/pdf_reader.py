import io
import re
from dataclasses import dataclass
from datetime import datetime

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def _extract_money(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace(",", "").replace("$", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_percent(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace("%", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


@dataclass
class ParsedOffer:
    role_title: str | None
    level: str | None
    location: str | None
    base_salary: float | None
    bonus_target: float | None
    equity_type: str | None
    equity_amount: float | None
    vesting_schedule: str | None
    start_date: datetime | None
    confidence_note: str


def parse_offer_text(text: str) -> ParsedOffer:
    role_title = _extract_text(text, r"(?:role|position|title)\s*[:\-]\s*([^\n]+)")
    level = _extract_text(text, r"(?:level|seniority)\s*[:\-]\s*([^\n]+)")
    location = _extract_text(text, r"(?:location)\s*[:\-]\s*([^\n]+)")
    base_salary = _extract_money(text, r"(?:base(?:\s+salary)?|salary)\s*[:\-]?\s*\$?\s*([0-9,]+)")
    bonus_target = _extract_percent(text, r"(?:bonus(?:\s+target)?)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%")
    equity_amount = _extract_money(text, r"(?:equity|stock|rsu(?:s)?)\s*(?:amount|value)?\s*[:\-]?\s*\$?\s*([0-9,]+)")
    equity_type = _extract_text(text, r"(?:equity\s+type|stock\s+type)\s*[:\-]\s*([^\n]+)")
    vesting_schedule = _extract_text(text, r"(?:vesting(?:\s+schedule)?)\s*[:\-]\s*([^\n]+)")
    start_raw = _extract_text(text, r"(?:start\s+date)\s*[:\-]\s*([^\n]+)")

    start_date = None
    if start_raw:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                start_date = datetime.strptime(start_raw, fmt)
                break
            except ValueError:
                continue

    populated = sum(
        value is not None
        for value in [role_title, level, location, base_salary, bonus_target, equity_amount, vesting_schedule]
    )
    confidence_note = (
        "Parsed from regex heuristics; review values before final evaluation."
        if populated >= 3
        else "Low-confidence parse; PDF format likely differs from expected labels."
    )

    return ParsedOffer(
        role_title=role_title,
        level=level,
        location=location,
        base_salary=base_salary,
        bonus_target=bonus_target,
        equity_type=equity_type,
        equity_amount=equity_amount,
        vesting_schedule=vesting_schedule,
        start_date=start_date,
        confidence_note=confidence_note,
    )
