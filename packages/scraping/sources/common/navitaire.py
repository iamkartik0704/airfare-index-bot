"""Shared adapter for airlines on the Navitaire dotREZ booking platform.

IndiGo, Air India Express and Akasa Air sell through dotREZ-based booking
apps whose availability call returns ``data.trips[].journeysAvailable[]``
with per-fare ``serviceCharges``. The per-airline adapters only declare the
search page path, the XHR pattern and the URL parameters; the parsing rules
live here once (no duplicated parsing logic).

Fixtures for these adapters are modelled on this payload shape and must be
refreshed from genuine captures (``scripts/scraper/capture_fixture.py``)
before a source is enabled.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.scraping.core.exceptions import ParseError
from packages.scraping.core.fetchers.base import FetchRequest, FetchResponse
from packages.scraping.sources.base import BaseSourceAdapter

#: Service-charge codes that are airport levies rather than government taxes.
AIRPORT_FEE_CODES = frozenset({"UDF", "ASF", "PSF", "ADF", "DF"})


class NavitaireAdapter(BaseSourceAdapter):
    """Browser navigation to the public search page + capture of its availability XHR."""

    capabilities = ("xhr_json", "fare_breakdown", "sold_out", "seats_left", "fare_family")
    SEARCH_PATH: ClassVar[str]
    XHR_PATTERN: ClassVar[str]
    #: Query-string parameter names used by the airline's search page.
    PARAM_NAMES: ClassVar[dict[str, str]] = {
        "origin": "origin",
        "destination": "destination",
        "date": "departureDate",
        "adults": "adults",
    }
    EXTRA_PARAMS: ClassVar[dict[str, str]] = {"tripType": "OneWay", "currency": "INR"}

    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        names = self.PARAM_NAMES
        query = urlencode(
            {
                names["origin"]: context.origin,
                names["destination"]: context.destination,
                names["date"]: context.travel_date.isoformat(),
                names["adults"]: context.adults,
                **self.EXTRA_PARAMS,
            }
        )
        return [
            FetchRequest(
                url=f"{self.definition.base_url}{self.SEARCH_PATH}?{query}",
                capture_xhr=self.XHR_PATTERN,
                headers={"Accept": "application/json"},
            )
        ]

    def parse(self, response: FetchResponse, context: ScrapeContext) -> list[RawFareQuote]:
        trips = _require(response.json(), "data", "trips")
        if not isinstance(trips, list):
            raise ParseError("data.trips is not a list", source=self.source_id)
        quotes: list[RawFareQuote] = []
        for trip in trips:
            for journey in _require(trip, "journeysAvailable"):
                quotes.extend(self._journey_quotes(journey, context))
        return quotes

    def _journey_quotes(
        self, journey: dict[str, Any], context: ScrapeContext
    ) -> list[RawFareQuote]:
        designator = _require(journey, "designator")
        if (designator.get("origin"), designator.get("destination")) != (
            context.origin,
            context.destination,
        ):
            return []  # itineraries the site lists for another city-pair
        segments = _require(journey, "segments")
        carrier = str(_require(segments[0], "identifier", "carrierCode"))
        flight = "/".join(
            f"{s['identifier']['carrierCode']}{s['identifier']['identifier']}" for s in segments
        )
        common = {
            "carrier": carrier,
            "flight_number": flight,
            "departure_time": str(designator.get("departure")),
            "arrival_time": str(designator.get("arrival")),
            "stops": str(journey.get("stops", len(segments) - 1)),
            "currency": "INR",
        }
        fares = journey.get("fares") or []
        if journey.get("isSoldOut") or not fares:
            return [RawFareQuote(**common, availability="SOLD_OUT")]
        return [self._fare_quote(fare, common) for fare in fares]

    def _fare_quote(self, fare: dict[str, Any], common: dict[str, str]) -> RawFareQuote:
        adult = next(
            (p for p in _require(fare, "passengerFares") if p.get("passengerType") == "ADT"),
            None,
        )
        if adult is None:
            raise ParseError("fare without an adult passenger fare", source=self.source_id)
        base = taxes = airport = 0.0
        breakdown: list[str] = []
        for charge in _require(adult, "serviceCharges"):
            amount = float(charge["amount"])
            kind, code = str(charge.get("type")), str(charge.get("code") or "")
            breakdown.append(f"{kind}/{code}:{amount}")
            if kind == "FarePrice":
                base += amount
            elif kind == "Tax" and code in AIRPORT_FEE_CODES:
                airport += amount
            elif kind in {"Tax", "Fee", "Surcharge"}:
                taxes += amount
        if base <= 0:
            raise ParseError("fare has no FarePrice component", source=self.source_id)
        return RawFareQuote(
            **common,
            fare_class=str(fare.get("fareFamily") or fare.get("productClass") or ""),
            base_fare=_money(base),
            taxes=_money(taxes),
            airport_fees=_money(airport),
            convenience_fee="0",
            total_fare=_money(base + taxes + airport),
            seats_left=str(fare["availableCount"]) if "availableCount" in fare else None,
            availability="AVAILABLE",
            extra={
                "charges": json.dumps(breakdown),
                "product_class": str(fare.get("productClass")),
            },
        )


def _money(value: float) -> str:
    return f"{value:.2f}"


def _require(node: Any, *path: str) -> Any:
    current = node
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise ParseError("expected field missing from payload", field=".".join(path))
        current = current[key]
    return current
