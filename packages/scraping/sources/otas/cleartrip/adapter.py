"""Cleartrip — rendered results page (OTA)."""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class CleartripAdapter(DomCardAdapter):
    source_id = "cleartrip"
    parser_version = "1"
    health_markers = ("Cleartrip",)
    SPEC = CardSpec(
        card=("[data-testid='airlineBlock']", ".flight-listing-card"),
        airline=("[data-testid='airlineName']",),
        flight_number=("[data-testid='flightNumber']",),
        total_fare=("[data-testid='airlinePrice']",),
        fare_family=("[data-testid='fareType']",),
        departure=("[data-testid='departureTime']",),
        arrival=("[data-testid='arrivalTime']",),
        stops=("[data-testid='stops']",),
        convenience_fee=("[data-testid='convenienceFee']",),
        no_results=("[data-testid='noResults']",),
    )

    def search_url(self, context: ScrapeContext) -> str:
        query = urlencode(
            {
                "adults": context.adults,
                "childs": 0,
                "infants": 0,
                "class": "Economy",
                "depart_date": context.travel_date.strftime("%d/%m/%Y"),
                "from": context.origin,
                "to": context.destination,
                "intl": "n",
            }
        )
        return f"{self.definition.base_url}/flights/results?{query}"
