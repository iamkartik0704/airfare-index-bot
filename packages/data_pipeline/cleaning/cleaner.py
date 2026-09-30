"""Text → typed value coercion (doc 07 phase 2).

Sources display fares as text in many shapes: ``"₹ 5,400"``, ``"Rs.5400/-"``,
``"INR 1,05,000.50"`` (Indian lakh grouping), ``"5.400,00"``. These helpers
return ``Decimal`` / ``int`` or ``None`` when the text carries no amount —
they never guess and never return a silent zero for garbage (the old
``clean_price`` returned ``0.0`` on failure, which would have poisoned the index).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from packages.data_pipeline.exceptions import CleaningError

_CURRENCY_TOKENS = re.compile(r"(₹|rs\.?|inr|/-)", re.IGNORECASE)
_ZERO_WORDS = frozenset({"free", "nil", "none", "waived", "included"})
_MISSING_WORDS = frozenset({"", "-", "—", "–", "n/a", "na", "null"})
_EURO_STYLE = re.compile(r"^\d{1,3}(\.\d{3})+,\d{1,2}$")
_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_EMBEDDED_AMOUNT = re.compile(r"\d[\d,]*(?:\.\d+)?")
_INT_IN_TEXT = re.compile(r"\d+")
TWO_PLACES = Decimal("0.01")


def parse_money(text: str | None) -> Decimal | None:
    """Parse a displayed rupee amount. ``None`` = not displayed. Raises on garbage."""
    if text is None:
        return None
    cleaned = _CURRENCY_TOKENS.sub("", text).strip().lower()
    cleaned = cleaned.replace(" ", "").replace(" ", "")
    if cleaned in _MISSING_WORDS:
        return None
    if cleaned in _ZERO_WORDS:
        return Decimal("0.00")
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    if _EURO_STYLE.match(cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    if not _NUMBER.match(cleaned):
        cleaned = _embedded_rupee_amount(text)
    try:
        return Decimal(cleaned).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise CleaningError("unparseable amount", text=text) from exc


def _embedded_rupee_amount(text: str) -> str:
    """``"+ ₹349 convenience fee"`` → ``"349"``.

    Only for text that explicitly carries a rupee marker and exactly one amount;
    anything else is ambiguous and raises (never guess a price).
    """
    if not _CURRENCY_TOKENS.search(text):
        raise CleaningError("unparseable amount", text=text)
    amounts = _EMBEDDED_AMOUNT.findall(text)
    if len(amounts) != 1:
        raise CleaningError("unparseable amount", text=text)
    return str(amounts[0]).replace(",", "")


def parse_first_int(text: str | None) -> int | None:
    """``"4 seats left"`` → 4; ``None``/no digits → ``None``."""
    if text is None:
        return None
    match = _INT_IN_TEXT.search(text)
    return int(match.group()) if match else None


def parse_stops(text: str | None) -> int | None:
    if text is None:
        return None
    lowered = text.strip().lower()
    if lowered in {"non-stop", "nonstop", "direct", "0", "non stop"}:
        return 0
    return parse_first_int(lowered)


def parse_departure(text: str | None, travel_date: date) -> datetime | None:
    """Accepts ISO datetimes (``2026-10-07T06:05:00``) or clock times (``06:05``).

    Returned value is naive local time (IST) — the caller attaches the zone.
    """
    if not text:
        return None
    raw = text.strip()
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%H.%M"):
        try:
            clock: time = datetime.strptime(raw.upper(), fmt).time()
            return datetime.combine(travel_date, clock)
        except ValueError:
            continue
    raise CleaningError("unparseable departure time", text=text)


def normalize_flight_number(text: str | None) -> str | None:
    """``"6E 2134"`` → ``"6E2134"``; multi-segment ``"6E711/6E404"`` preserved."""
    if text is None:
        return None
    parts = [re.sub(r"[\s\-]", "", p).upper() for p in re.split(r"[/,+]", text) if p.strip()]
    return "/".join(parts) or None
