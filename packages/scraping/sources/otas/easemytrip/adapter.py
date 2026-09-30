"""EaseMyTrip — rendered listing page (OTA).

robots.txt (2026-09-30) disallows ``/flight-search/listing*``; governance
refuses these requests until the policy changes.
"""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class EasemytripAdapter(DomCardAdapter):
    source_id = "easemytrip"
    parser_version = "1"
    health_markers = ("EaseMyTrip",)
    SPEC = CardSpec(
        card=(".fltResult .row-flight", ".flight-row"),
        airline=(".txt-r4",),
        flight_number=(".txt-r5",),
        total_fare=(".txt-r6-n",),
        fare_family=(".fare-name",),
        departure=(".txt-r2-n",),
        arrival=(".txt-r2-n.arr",),
        stops=(".txt-r3",),
        convenience_fee=(".conv-fee",),
        no_results=(".no-flight-found",),
    )

    def search_url(self, context: ScrapeContext) -> str:
        date = context.travel_date.strftime("%d/%m/%Y")
        query = urlencode(
            {
                "srch": f"{context.origin}|{context.destination}|{date}",
                "px": f"{context.adults}-0-0",
            }
        )
        return f"{self.definition.base_url}/flight-search/listing?{query}"
