"""ixigo — rendered results page (OTA).

robots.txt (2026-09-30) disallows ``/search/result/`` and sets Crawl-delay 10;
governance refuses these requests until the policy changes.
"""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class IxigoAdapter(DomCardAdapter):
    source_id = "ixigo"
    parser_version = "1"
    health_markers = ("ixigo",)
    SPEC = CardSpec(
        card=(".flight-listing-item", "[data-testid='flight-card']"),
        airline=(".airline-text",),
        flight_number=(".flight-code",),
        total_fare=(".price-text",),
        fare_family=(".fare-class",),
        departure=(".dep-time",),
        arrival=(".arr-time",),
        stops=(".stops-text",),
        convenience_fee=(".conv-fee",),
        no_results=(".no-results",),
    )

    def search_url(self, context: ScrapeContext) -> str:
        query = urlencode(
            {
                "from": context.origin,
                "to": context.destination,
                "date": context.travel_date.strftime("%d%m%Y"),
                "adults": context.adults,
                "class": "e",
            }
        )
        return f"{self.definition.base_url}/search/result/flight?{query}"
