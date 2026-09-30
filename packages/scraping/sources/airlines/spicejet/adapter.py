"""SpiceJet (SG) — rendered results page.

robots.txt disallows ``/api/v1``, so the availability XHR is *not* captured;
the adapter reads only the rendered public results page.
"""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class SpicejetAdapter(DomCardAdapter):
    source_id = "spicejet"
    parser_version = "1"
    health_markers = ("SpiceJet",)
    CARRIER = "SG"
    SPEC = CardSpec(
        card=("[data-testid='flight-card']", ".flight-card"),
        flight_number=("[data-testid='flight-number']", ".flight-number"),
        total_fare=("[data-testid='fare-total']", ".fare-amount"),
        fare_family=("[data-testid='fare-name']", ".fare-name"),
        departure=("[data-testid='dep-time']",),
        arrival=("[data-testid='arr-time']",),
        stops=("[data-testid='stops']",),
        seats_left=("[data-testid='seats-left']",),
        sold_out=("[data-testid='sold-out']",),
        no_results=("[data-testid='no-flights']",),
    )

    def search_url(self, context: ScrapeContext) -> str:
        query = urlencode(
            {
                "from": context.origin,
                "to": context.destination,
                "date": context.travel_date.isoformat(),
                "adt": context.adults,
                "currency": "INR",
            }
        )
        return f"{self.definition.base_url}/search?{query}"
