"""Yatra — rendered listing page (OTA)."""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class YatraAdapter(DomCardAdapter):
    source_id = "yatra"
    parser_version = "1"
    health_markers = ("Yatra",)
    SPEC = CardSpec(
        card=(".flightItem", "[data-flight-card]"),
        airline=(".airline-name",),
        flight_number=(".flight-no",),
        total_fare=(".fare-price", ".total-price"),
        fare_family=(".fare-type",),
        departure=(".depart-time",),
        arrival=(".arrive-time",),
        stops=(".stops",),
        convenience_fee=(".conv-fee",),
        seats_left=(".seat-left",),
        no_results=(".no-flights",),
    )

    def search_url(self, context: ScrapeContext) -> str:
        query = urlencode(
            {
                "type": "O",
                "origin": context.origin,
                "destination": context.destination,
                "flight_depart_date": context.travel_date.strftime("%d/%m/%Y"),
                "ADT": context.adults,
                "CHD": 0,
                "INF": 0,
                "class": "Economy",
            }
        )
        return f"{self.definition.base_url}/air-search-ui/dom2/trigger?{query}"
