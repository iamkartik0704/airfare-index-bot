"""FastAPI application factory (doc 11).

The schema is managed by Alembic (``alembic upgrade head``); the API never
creates tables. Run with::

    uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.api.errors import install_error_handlers
from apps.api.middleware import RequestContextMiddleware
from apps.api.routers import ALL_ROUTERS
from packages.config.settings import get_settings
from packages.observability.logging import configure_logging
from packages.observability.metrics.metrics import REGISTRY

API_DESCRIPTION = """
Real-time Airfare Price Index (APIx) for India — SIH 26056 (MoSPI).

Every analytical response carries `data_origin` (`live`, `simulated`, `mixed`)
so synthetic demonstration data is never mistaken for observed fares.
Operator and bulk-data endpoints require an `X-API-Key` header.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    app = FastAPI(
        title="SAFAR APIx API",
        version="1.0.0",
        description=API_DESCRIPTION,
        openapi_tags=[
            {"name": "index", "description": "Headline and sub-indices"},
            {"name": "routes", "description": "Basket routes and lead-time elasticity"},
            {"name": "analytics", "description": "Heatmaps, carriers, channels, cleaning funnel"},
            {"name": "fares", "description": "Normalized observations and lineage"},
            {"name": "system", "description": "Source health and data freshness"},
            {"name": "jobs", "description": "Scrape jobs and sweeps"},
            {"name": "validation", "description": "DGCA back-test and methodology"},
            {"name": "data", "description": "Protected bulk exports"},
        ],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    install_error_handlers(app)
    for router in ALL_ROUTERS:
        app.include_router(router)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "SAFAR APIx API", "docs": "/docs", "health": "/api/v1/system/health"}

    return app


app = create_app()
