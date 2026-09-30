"""In-process fetcher for ``sim://`` URLs (decision D8).

Implements ``BaseFetcher`` so the simulator travels the exact same path as a
real source: governed fetch → evidence → parse → pipeline. Responses are JSON
shaped like an OTA search API with *display strings* ("₹5,263",
"Non-stop", "4 seats left") so the cleaning stage is genuinely exercised.

About 1 % of searches fail once with HTTP 503 (deterministically per URL) to
exercise the retry path; the retry then succeeds.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, date, datetime
from urllib.parse import parse_qs, urlsplit

from packages.config.reference import get_reference_data
from packages.domain.enums import FetchMode
from packages.scraping.core.exceptions import NetworkError
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.sources.simulated.market import MarketModel, SimFare

TRANSIENT_FAILURE_RATE = 0.01


def _rupees(amount: float) -> str:
    return f"₹{amount:,.0f}"


def _render(fare: SimFare) -> dict[str, object]:
    card: dict[str, object] = {
        "airline": fare.carrier_name,
        "flight_no": f"{fare.flight_number[:2]} {fare.flight_number[2:]}",
        "departure": fare.departure.strftime("%H:%M"),
        "arrival": fare.arrival.strftime("%H:%M"),
        "stops": "Non-stop",
        "fare_type": fare.fare_family,
        "status": fare.status,
    }
    if fare.status == "Available":
        card["price"] = {
            "base": _rupees(fare.base_fare),
            "taxes": _rupees(fare.taxes),
            "airport_fees": _rupees(fare.airport_fees),
            "convenience_fee": _rupees(fare.convenience_fee),
            "total": _rupees(fare.total_fare),
        }
        if fare.seats_left is not None:
            card["seats_left"] = f"{fare.seats_left} seat{'s' if fare.seats_left > 1 else ''} left"
    return card


class SimulatedFetcher(BaseFetcher):
    mode = FetchMode.SIMULATED

    def __init__(
        self,
        market: MarketModel | None = None,
        *,
        transient_failure_rate: float = TRANSIENT_FAILURE_RATE,
    ) -> None:
        if market is None:
            ref = get_reference_data()
            market = MarketModel(ref.basket, ref.carriers)
        self._market = market
        self._failed_once: set[str] = set()
        self._failure_rate = transient_failure_rate

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        started = time.perf_counter()
        parts = urlsplit(request.url)
        if parts.scheme != "sim":
            raise NetworkError("simulated fetcher only serves sim:// URLs", url=request.url)
        query = {k: v[0] for k, v in parse_qs(parts.query).items()}
        try:
            route = f"{query['origin']}-{query['destination']}"
            travel = date.fromisoformat(query["travel_date"])
            observed = date.fromisoformat(query["observation_date"])
            channel = query.get("channel", "direct")
        except (KeyError, ValueError):
            return self._response(request, 400, {"error": "bad search"}, started)

        digest = int(hashlib.sha256(request.url.encode()).hexdigest()[:8], 16)
        if digest / 0xFFFFFFFF < self._failure_rate and request.url not in self._failed_once:
            self._failed_once.add(request.url)
            return self._response(request, 503, {"error": "upstream busy"}, started)

        try:
            fares = self._market.fares(route, travel, observed, channel)
        except KeyError:
            return self._response(request, 404, {"error": f"unknown route {route}"}, started)
        payload = {
            "search": {
                "origin": query["origin"],
                "destination": query["destination"],
                "date": travel.isoformat(),
                "channel": channel,
                "currency": "INR",
            },
            "results": [_render(f) for f in fares],
            "synthetic": True,
        }
        return self._response(request, 200, payload, started)

    @staticmethod
    def _response(
        request: FetchRequest, status: int, payload: dict[str, object], started: float
    ) -> FetchResponse:
        return FetchResponse(
            request=request,
            url=request.url,
            status=status,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"content-type": "application/json; charset=utf-8"},
            fetch_mode=FetchMode.SIMULATED,
            fetched_at=datetime.now(UTC),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
