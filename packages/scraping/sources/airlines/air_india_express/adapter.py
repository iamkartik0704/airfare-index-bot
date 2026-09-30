"""Air India Express (IX) — Navitaire dotREZ availability capture.

robots.txt (2026-09-30) disallows ``/flight-availability``, which is the
results page this adapter would open; the governance layer therefore refuses
every request until the policy changes. The adapter exists so onboarding is a
policy decision, not an engineering task.
"""

from __future__ import annotations

from packages.scraping.sources.common.navitaire import NavitaireAdapter


class AirIndiaExpressAdapter(NavitaireAdapter):
    source_id = "air_india_express"
    parser_version = "1"
    health_markers = ("Air India Express",)

    SEARCH_PATH = "/flight-availability"
    XHR_PATTERN = "/api/v1/availability"
