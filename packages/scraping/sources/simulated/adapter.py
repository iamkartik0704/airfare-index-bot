"""Adapters for the synthetic market (decision D8).

Two channels are simulated so cross-channel deduplication and the
airline-vs-OTA convenience-fee wedge can be demonstrated:

* ``simulated``      — airline-direct channel, no convenience fee;
* ``simulated_ota``  — OTA channel, same flights, adds a convenience fee.
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.scraping.core.exceptions import ParseError
from packages.scraping.core.fetchers.base import FetchRequest, FetchResponse
from packages.scraping.sources.base import BaseSourceAdapter

_STATUS = {"Available": "AVAILABLE", "Sold out": "SOLD_OUT", "Cancelled": "CANCELLED"}


class _SimulatedAdapter(BaseSourceAdapter):
    parser_version = "1"
    capabilities = ("json", "fare_breakdown", "sold_out", "cancelled", "seats_left", "synthetic")
    channel: ClassVar[str]

    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        query = urlencode(
            {
                "origin": context.origin,
                "destination": context.destination,
                "travel_date": context.travel_date.isoformat(),
                "observation_date": context.observation_date.isoformat(),
                "channel": self.channel,
            }
        )
        return [FetchRequest(url=f"{self.definition.base_url}/search?{query}")]

    def parse(self, response: FetchResponse, context: ScrapeContext) -> list[RawFareQuote]:
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ParseError("payload has no results list", source=self.source_id)
        search = payload.get("search") or {}
        if (search.get("origin"), search.get("destination")) != (
            context.origin,
            context.destination,
        ):
            raise ParseError("response is for a different search", source=self.source_id)
        return [self._quote(card) for card in payload["results"]]

    def _quote(self, card: dict[str, Any]) -> RawFareQuote:
        status = _STATUS.get(str(card.get("status")))
        if status is None:
            raise ParseError("unknown fare status", status=card.get("status"))
        price = card.get("price") or {}
        return RawFareQuote(
            carrier=card.get("airline"),
            flight_number=card.get("flight_no"),
            fare_class=card.get("fare_type"),
            departure_time=card.get("departure"),
            arrival_time=card.get("arrival"),
            stops=card.get("stops"),
            base_fare=price.get("base"),
            taxes=price.get("taxes"),
            airport_fees=price.get("airport_fees"),
            convenience_fee=price.get("convenience_fee"),
            total_fare=price.get("total"),
            currency="INR",
            seats_left=card.get("seats_left"),
            availability=status,
        )


class SimulatedAirlineAdapter(_SimulatedAdapter):
    source_id = "simulated"
    channel = "direct"


class SimulatedOtaAdapter(_SimulatedAdapter):
    source_id = "simulated_ota"
    channel = "ota"
