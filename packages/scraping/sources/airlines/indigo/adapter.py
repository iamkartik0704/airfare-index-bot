"""IndiGo (6E) — the Stage 3 reference adapter (doc 17).

Strategy: open the public one-way search page in a browser and capture the
availability JSON the booking app requests (doc 04 "XHR/API Capture"), rather
than scraping the React DOM. Parsing is shared with the other Navitaire
dotREZ airlines (``sources/common/navitaire.py``).

The search path and XHR pattern are class constants so a site change is a
one-line fix; the parser is validated offline against
``tests/fixtures/json/indigo/`` (modelled payloads — refresh from a genuine
capture with ``scripts/scraper/capture_fixture.py`` before enabling).
"""

from __future__ import annotations

from packages.scraping.sources.common.navitaire import NavitaireAdapter


class IndigoAdapter(NavitaireAdapter):
    source_id = "indigo"
    parser_version = "1"
    health_markers = ("IndiGo",)

    SEARCH_PATH = "/booking/flight-select.html"
    XHR_PATTERN = "/v1/availability/search"
