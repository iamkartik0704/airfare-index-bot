"""Fare explorer: normalized observations and their lineage."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from apps.api.dependencies.db import AppSettings, DbSession
from apps.api.repositories.fares_read import FareFilter
from apps.api.schemas.common import Page
from apps.api.schemas.operations import FareLineage, FareOut
from apps.api.services.analytics_service import AnalyticsService
from packages.domain.enums import QualityFlag

router = APIRouter(prefix="/api/v1/fares", tags=["fares"])


@router.get("", response_model=Page[FareOut])
def list_fares(
    session: DbSession,
    settings: AppSettings,
    route: str | None = Query(None, pattern=r"^[A-Z]{3}-[A-Z]{3}$"),
    observation_date: date | None = None,
    travel_date: date | None = None,
    purchase_window: int | None = Query(None, ge=0, le=365),
    carrier: str | None = Query(None, pattern=r"^[A-Z0-9]{2}$"),
    source: str | None = Query(None, max_length=32),
    quality_flag: QualityFlag | None = None,
    canonical_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[FareOut]:
    """Latest normalized observations (newest first) with filters and pagination."""
    fare_filter = FareFilter(
        route=route,
        observation_date=observation_date,
        travel_date=travel_date,
        purchase_window=purchase_window,
        carrier=carrier,
        source=source,
        quality_flag=quality_flag,
        canonical_only=canonical_only,
    )
    return AnalyticsService(session, settings).fares_page(fare_filter, limit, offset)


@router.get("/{fare_id}", response_model=FareLineage)
def fare_lineage(fare_id: int, session: DbSession, settings: AppSettings) -> FareLineage:
    """A fare with its raw parser output, source response and scrape job (auditability)."""
    return AnalyticsService(session, settings).fare_lineage(fare_id)
