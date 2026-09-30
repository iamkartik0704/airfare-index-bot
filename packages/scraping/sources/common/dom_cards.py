"""Shared adapter for sources whose rendered results page lists one card per fare.

Most OTAs (and SpiceJet's public results page) render a list of flight cards.
Rather than re-implementing the same loop per source, an adapter declares a
``CardSpec``: ordered CSS selector fallbacks per field (doc 19 "adaptive
selectors" — a site redesign usually only needs a new first selector), the
markers that mean "sold out" and "no flights". The parser:

* raises ``ParseError`` when the page has neither cards nor a no-results
  marker (layout changed — never silently returns zero quotes);
* raises ``ParseError`` when a card lacks a flight number (mandatory);
* returns every other field as raw text for the pipeline to clean.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import ClassVar

from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.scraping.core.exceptions import ParseError
from packages.scraping.core.fetchers.base import FetchRequest, FetchResponse, Selector
from packages.scraping.sources.base import BaseSourceAdapter

Selectors = tuple[str, ...]


@dataclass(frozen=True)
class CardSpec:
    card: Selectors
    flight_number: Selectors
    total_fare: Selectors
    airline: Selectors = ()
    fare_family: Selectors = ()
    departure: Selectors = ()
    arrival: Selectors = ()
    stops: Selectors = ()
    base_fare: Selectors = ()
    taxes: Selectors = ()
    convenience_fee: Selectors = ()
    seats_left: Selectors = ()
    #: Selectors or lowercase text fragments marking a sold-out card.
    sold_out: Selectors = ()
    sold_out_text: tuple[str, ...] = ("sold out", "no seats")
    #: Selectors present on an explicit "no flights found" page.
    no_results: Selectors = ()
    extra: dict[str, Selectors] = field(default_factory=dict)


class DomCardAdapter(BaseSourceAdapter):
    capabilities = ("rendered_dom", "sold_out", "fare_family")
    SPEC: ClassVar[CardSpec]
    #: Carrier to assume when cards omit the airline name (single-airline sites).
    CARRIER: ClassVar[str | None] = None

    @abc.abstractmethod
    def search_url(self, context: ScrapeContext) -> str:
        """The public results-page URL for this search."""

    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        wait_for = ", ".join((*self.SPEC.card, *self.SPEC.no_results))
        return [FetchRequest(url=self.search_url(context), wait_for_selector=wait_for)]

    def parse(self, response: FetchResponse, context: ScrapeContext) -> list[RawFareQuote]:
        page = response.selector()
        cards = page.css(*self.SPEC.card)
        if not cards:
            if self.SPEC.no_results and page.css_first(*self.SPEC.no_results) is not None:
                return []
            raise ParseError(
                "no fare cards and no 'no results' marker: layout changed?",
                source=self.source_id,
                selectors="|".join(self.SPEC.card),
            )
        return [self._card(card) for card in cards]

    def _text(self, card: Selector, selectors: Selectors) -> str | None:
        return card.text(*selectors) if selectors else None

    def _card(self, card: Selector) -> RawFareQuote:
        spec = self.SPEC
        flight = card.require_text(*spec.flight_number, field_name="flight_number")
        whole = (card.text() or "").lower()
        sold_out = (spec.sold_out and card.css_first(*spec.sold_out) is not None) or any(
            marker in whole for marker in spec.sold_out_text
        )
        total = self._text(card, spec.total_fare)
        return RawFareQuote(
            carrier=self._text(card, spec.airline) or self.CARRIER,
            flight_number=flight,
            fare_class=self._text(card, spec.fare_family),
            departure_time=self._text(card, spec.departure),
            arrival_time=self._text(card, spec.arrival),
            stops=self._text(card, spec.stops),
            base_fare=self._text(card, spec.base_fare),
            taxes=self._text(card, spec.taxes),
            convenience_fee=self._text(card, spec.convenience_fee),
            total_fare=None if sold_out else total,
            seats_left=self._text(card, spec.seats_left),
            currency="INR",
            availability="SOLD_OUT" if sold_out else "AVAILABLE",
            extra={k: v for k, sels in spec.extra.items() if (v := card.text(*sels))},
        )
