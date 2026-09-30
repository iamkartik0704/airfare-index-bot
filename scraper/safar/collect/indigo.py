"""
IndiGo adapter — the reference implementation every other adapter copies.

One adapter per source, each owning its own selectors and query-string format.
Adding a carrier means adding a module here and one row to the registry in
`scraper/safar/collect/registry.py`; no other code changes.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date
from typing import Any

from .base import RawQuote, SelectorMap, SourceAdapter, departure_for, parse_rupees

FLIGHT_RE = re.compile(r"\b(6E|IX)\s?(\d{2,4})\b")


class IndiGoAdapter(SourceAdapter):
    def __init__(self) -> None:
        super().__init__(
            source_id="indigo",
            name="IndiGo (goIndiGo)",
            kind="airline",
            endpoint="https://www.goindigo.in/domestic-flights/search",
            carrier="6E",
            selectors=SelectorMap(
                container="[data-testid='flight-list-item']",
                fare_amount="[data-testid='price']",
                fare_class="[data-testid='fare-family']",
                flight_number="[data-testid='flight-number']",
                departure_time="[data-testid='departure-time']",
                seats_left="[data-testid='seat-availability']",
                baggage="[data-testid='baggage']",
            ),
            per_minute=6,
            crawl_delay=10,
        )

    def build_url(self, origin: str, destination: str, depart: date, adults: int = 1) -> str:
        query = urllib.parse.urlencode(
            {
                "tripType": "oneway",
                "origin": origin,
                "destination": destination,
                "departureDate": depart.isoformat(),
                "adults": adults,
                "class": "economy",
            }
        )
        return f"{self.endpoint}?{query}"

    def parse(self, page: Any, ctx: dict[str, Any]) -> list[RawQuote]:
        """`page` is the scrapling Response object; ctx carries the search we issued."""
        quotes: list[RawQuote] = []
        
        def extract_text(node, selector):
            els = node.css(selector)
            return els[0].xpath('string()').get().strip() if els else ""

        for block in page.css(self.selectors.container):
            fare = extract_text(block, self.selectors.fare_amount)
            if not fare:
                continue
            flight_raw = extract_text(block, self.selectors.flight_number)
            match = FLIGHT_RE.search(flight_raw.replace(" ", ""))
            
            fare_class = extract_text(block, self.selectors.fare_class)
            
            quotes.append(
                RawQuote(
                    source_id=self.source_id,
                    carrier=self.carrier or "6E",
                    route_id=ctx["route_id"],
                    origin=ctx["origin"],
                    destination=ctx["destination"],
                    departure=departure_for(ctx["day"], ctx["lead"]),
                    lead_time=ctx["lead"],
                    fare_class=fare_class or "VALUE",
                    flight_no=match.group(0) if match else flight_raw,
                    fare_text=fare,
                    tax_text="inclusive of taxes",
                    fee_text="—",
                    seats_left=_int(extract_text(block, self.selectors.seats_left)),
                    refundable="flex" in fare_class.lower(),
                    baggage_kg=15 if "lite" in fare_class.lower() else 25,
                    collected_at=ctx["collected_at"],
                )
            )
        return quotes


class MakeMyTripAdapter(SourceAdapter):
    """OTA adapter: all carriers on one page, with the convenience fee attached."""

    def __init__(self) -> None:
        super().__init__(
            source_id="makemytrip",
            name="MakeMyTrip",
            kind="ota",
            endpoint="https://www.makemytrip.com/flight-search",
            carrier=None,
            selectors=SelectorMap(
                container="[data-type='flight']",
                fare_amount=".fareSummary",
                fare_class=".fare-type",
                flight_number=".flight-no",
                departure_time=".flight-dep",
                seats_left=".seat-count",
                baggage=".baggage-info",
            ),
            per_minute=4,
            crawl_delay=15,
        )

    def build_url(self, origin: str, destination: str, depart: date, adults: int = 1) -> str:
        query = urllib.parse.urlencode(
            {
                "addToAirport": origin,
                "toAirport": destination,
                "departDate": depart.isoformat(),
                "adults": adults,
                "class": "E",
            }
        )
        return f"{self.endpoint}?{query}"

    def parse(self, page: Any, ctx: dict[str, Any]) -> list[RawQuote]:
        quotes: list[RawQuote] = []
        
        def extract_text(node, selector):
            els = node.css(selector)
            return els[0].xpath('string()').get().strip() if els else ""

        for block in page.css(self.selectors.container):
            fare = extract_text(block, self.selectors.fare_amount)
            if not fare:
                continue
            flight_raw = extract_text(block, self.selectors.flight_number).replace(" ", "")
            carrier = flight_raw[:2] if len(flight_raw) >= 2 else "XX"
            
            fare_class = extract_text(block, self.selectors.fare_class)
            
            quotes.append(
                RawQuote(
                    source_id=self.source_id,
                    carrier=carrier,
                    route_id=ctx["route_id"],
                    origin=ctx["origin"],
                    destination=ctx["destination"],
                    departure=departure_for(ctx["day"], ctx["lead"]),
                    lead_time=ctx["lead"],
                    fare_class=fare_class or "VALUE",
                    flight_no=flight_raw,
                    fare_text=f"₹{int(parse_rupees(fare)):,}",
                    tax_text="inclusive of taxes",
                    fee_text="+ 48 convenience fee",
                    seats_left=_int(extract_text(block, self.selectors.seats_left)),
                    refundable="flex" in fare_class.lower(),
                    baggage_kg=15,
                    collected_at=ctx["collected_at"],
                )
            )
        return quotes


def _text(block: str, testid_or_class: str) -> str:
    pattern = re.compile(
        rf"[^>]*(?:data-testid|class)=[\"'][^\"']*{re.escape(testid_or_class)}[^\"']*[\"'][^>]*>([^<]*)",
        re.I,
    )
    match = pattern.search(block)
    return match.group(1).strip() if match else ""


def _int(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else 0
