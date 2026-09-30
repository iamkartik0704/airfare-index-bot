"""Akasa Air (QP) — Navitaire dotREZ availability capture."""

from __future__ import annotations

from typing import ClassVar

from packages.scraping.sources.common.navitaire import NavitaireAdapter


class AkasaAdapter(NavitaireAdapter):
    source_id = "akasa"
    parser_version = "1"
    health_markers = ("Akasa",)

    SEARCH_PATH = "/booking/select-flight"
    XHR_PATTERN = "/api/nsk/v1/availability/search"
    PARAM_NAMES: ClassVar[dict[str, str]] = {
        "origin": "from",
        "destination": "to",
        "date": "date",
        "adults": "adt",
    }
