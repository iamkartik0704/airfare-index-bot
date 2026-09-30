"""Air India (AI) — availability JSON captured from the booking app.

The booking app (Amadeus Digital Experience style) returns
``data.airBoundGroups[]`` — one per itinerary, with ``boundDetails.segments``
referencing ``dictionaries.flight`` — and ``airBounds[]`` per fare family
with ``prices.totalPrices[]``. Government taxes and airport charges are only
published as one ``totalTaxes`` figure, so ``airport_fees`` is reported as not
displayed (the pipeline records ``AIRPORT_FEES_MISSING``) rather than guessed.

Fixtures are modelled on this payload shape; refresh from a genuine capture
(``scripts/scraper/capture_fixture.py``) before enabling the source.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.scraping.core.exceptions import ParseError
from packages.scraping.core.fetchers.base import FetchRequest, FetchResponse
from packages.scraping.sources.base import BaseSourceAdapter


class AirIndiaAdapter(BaseSourceAdapter):
    source_id = "air_india"
    parser_version = "1"
    capabilities = ("xhr_json", "fare_breakdown", "sold_out", "seats_left", "fare_family")
    health_markers = ("Air India",)

    SEARCH_PATH = "/in/en/book/flight-search.html"
    XHR_PATTERN = "/v2/search/air-bounds"

    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        query = urlencode(
            {
                "from": context.origin,
                "to": context.destination,
                "departureDate": context.travel_date.isoformat(),
                "adt": context.adults,
                "cabin": "ECONOMY",
                "tripType": "ONE_WAY",
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
        payload = response.json()
        try:
            groups = payload["data"]["airBoundGroups"]
            flights = payload["dictionaries"]["flight"]
        except (KeyError, TypeError) as exc:
            raise ParseError("airBoundGroups/dictionaries missing", source=self.source_id) from exc
        quotes: list[RawFareQuote] = []
        for group in groups:
            details = group["boundDetails"]
            if (details.get("originLocationCode"), details.get("destinationLocationCode")) != (
                context.origin,
                context.destination,
            ):
                continue
            segments = [flights[s["flightId"]] for s in details["segments"]]
            common = self._common(segments)
            bounds = group.get("airBounds") or []
            if not bounds:
                quotes.append(RawFareQuote(**common, availability="SOLD_OUT"))
            quotes.extend(self._bound_quote(bound, common) for bound in bounds)
        return quotes

    @staticmethod
    def _common(segments: list[dict[str, Any]]) -> dict[str, str]:
        first, last = segments[0], segments[-1]
        return {
            "carrier": str(first["marketingAirlineCode"]),
            "flight_number": "/".join(
                f"{s['marketingAirlineCode']}{s['marketingFlightNumber']}" for s in segments
            ),
            "departure_time": str(first["departure"]["dateTime"]),
            "arrival_time": str(last["arrival"]["dateTime"]),
            "stops": str(len(segments) - 1),
            "currency": "INR",
        }

    def _bound_quote(self, bound: dict[str, Any], common: dict[str, str]) -> RawFareQuote:
        seats = min(
            (a.get("quota") for a in bound.get("availabilityDetails", []) if "quota" in a),
            default=None,
        )
        if bound.get("isSoldOut") or seats == 0:
            return RawFareQuote(
                **common,
                fare_class=_family_label(str(bound.get("fareFamilyCode", ""))),
                availability="SOLD_OUT",
            )
        prices = bound["prices"]["totalPrices"]
        if not prices:
            raise ParseError("air bound without a price", source=self.source_id)
        price = prices[0]
        if price.get("currencyCode") != "INR":
            raise ParseError("unexpected currency", currency=price.get("currencyCode"))
        return RawFareQuote(
            **common,
            fare_class=_family_label(str(bound.get("fareFamilyCode", ""))),
            base_fare=str(price["base"]),
            taxes=str(price["totalTaxes"]),
            convenience_fee="0",
            total_fare=str(price["total"]),
            seats_left=str(seats) if seats is not None else None,
            availability="AVAILABLE",
            extra={"fare_family_code": str(bound.get("fareFamilyCode"))},
        )


_FAMILIES = {
    "ECOVALUE": "Economy Value",
    "ECOCLASSIC": "Economy Classic",
    "ECOFLEX": "Economy Flex",
    "PREMFLEX": "Premium Economy",
    "BUSCLASSIC": "Business",
}


def _family_label(code: str) -> str:
    """Air India publishes family codes; map them to the displayed family names."""
    return _FAMILIES.get(code.upper(), code)
