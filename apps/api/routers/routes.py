"""Basket routes, route trends and lead-time elasticity (doc 11 ``/routes/{o}-{d}/trends``)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Path, Query

from apps.api.dependencies.db import AppSettings, DbSession, Reference
from apps.api.schemas.index import LeadTimeOut, RouteSummary, RouteTrends
from apps.api.services.index_service import IndexQueryService

router = APIRouter(prefix="/api/v1", tags=["routes"])
IATA_PATTERN = r"^[A-Z]{3}$"


@router.get("/routes", response_model=list[RouteSummary])
def routes(session: DbSession, settings: AppSettings, reference: Reference) -> list[RouteSummary]:
    return IndexQueryService(session, settings, reference).routes()


@router.get("/routes/{origin}-{destination}/trends", response_model=RouteTrends)
def route_trends(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    origin: str = Path(pattern=IATA_PATTERN),
    destination: str = Path(pattern=IATA_PATTERN),
    start_date: date | None = None,
    end_date: date | None = None,
) -> RouteTrends:
    """Route index history and its lead-time elasticity curve."""
    service = IndexQueryService(session, settings, reference)
    return service.route_trends(f"{origin}-{destination}", start_date, end_date)


@router.get("/analytics/lead-time", response_model=LeadTimeOut)
def lead_time(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    date_: date | None = Query(None, alias="date"),
    route: str | None = Query(None, pattern=r"^[A-Z]{3}-[A-Z]{3}$"),
) -> LeadTimeOut:
    """Basket (or route) fare by purchase window and the constant-elasticity fit."""
    return IndexQueryService(session, settings, reference).lead_time(date_, route)
