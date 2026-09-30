"""MakeMyTrip — rendered listing page (OTA; convenience fee shown per card)."""

from __future__ import annotations

from urllib.parse import urlencode

from packages.domain.models.job import ScrapeContext
from packages.scraping.sources.common.dom_cards import CardSpec, DomCardAdapter


class MakemytripAdapter(DomCardAdapter):
    source_id = "makemytrip"
    parser_version = "1"
    health_markers = ("MakeMyTrip",)
    SPEC = CardSpec(
        card=(".listingCard", "[data-test='component-flight-card']"),
        airline=(".airlineName", "[data-test='airline-name']"),
        flight_number=(".fliCode", "[data-test='flight-code']"),
        total_fare=(".priceSection .fontSize18", "[data-test='fare-total']"),
        fare_family=(".fareFamilyName", "[data-test='fare-family']"),
        departure=(".timeInfoLeft .flightTimeInfo", "[data-test='dep-time']"),
        arrival=(".timeInfoRight .flightTimeInfo", "[data-test='arr-time']"),
        stops=(".stop-info", "[data-test='stops']"),
        convenience_fee=(".convFee", "[data-test='convenience-fee']"),
        seats_left=(".seatsLeft",),
        no_results=(".noResultsFound", "[data-test='no-results']"),
    )

    def search_url(self, context: ScrapeContext) -> str:
        date = context.travel_date.strftime("%d/%m/%Y")
        query = urlencode(
            {
                "itinerary": f"{context.origin}-{context.destination}-{date}",
                "tripType": "O",
                "paxType": f"A-{context.adults}_C-0_I-0",
                "intl": "false",
                "cabinClass": "E",
            }
        )
        return f"{self.definition.base_url}/flight/search?{query}"
