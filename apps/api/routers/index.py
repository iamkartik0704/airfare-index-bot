"""Headline APIx and sub-indices (doc 11 ``/api/v1/index/*``)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from apps.api.dependencies.db import AppSettings, DbSession, Reference
from apps.api.schemas.index import Headline, IndexSeries, Lineage, SubIndices
from apps.api.services.index_service import IndexQueryService
from packages.domain.enums import IndexFrequency, IndexScope

router = APIRouter(prefix="/api/v1/index", tags=["index"])

ScopeQ = Query(IndexScope.HEADLINE, description="HEADLINE, WINDOW, REGION or ROUTE")
KeyQ = Query("", max_length=16, description="e.g. T+7, South, DEL-BOM (empty for HEADLINE)")


def _series(
    freq: IndexFrequency,
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    start_date: date | None,
    end_date: date | None,
    scope: IndexScope,
    key: str,
) -> IndexSeries:
    service = IndexQueryService(session, settings, reference)
    return service.series(freq, scope, key, start_date, end_date)


@router.get("/daily", response_model=IndexSeries)
def daily(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    start_date: date | None = None,
    end_date: date | None = None,
    scope: IndexScope = ScopeQ,
    key: str = KeyQ,
) -> IndexSeries:
    """Daily APIx for a date range, with a trailing rolling mean."""
    return _series(
        IndexFrequency.DAILY, session, settings, reference, start_date, end_date, scope, key
    )


@router.get("/weekly", response_model=IndexSeries)
def weekly(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    start_date: date | None = None,
    end_date: date | None = None,
    scope: IndexScope = ScopeQ,
    key: str = KeyQ,
) -> IndexSeries:
    return _series(
        IndexFrequency.WEEKLY, session, settings, reference, start_date, end_date, scope, key
    )


@router.get("/monthly", response_model=IndexSeries)
def monthly(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    start_date: date | None = None,
    end_date: date | None = None,
    scope: IndexScope = ScopeQ,
    key: str = KeyQ,
) -> IndexSeries:
    return _series(
        IndexFrequency.MONTHLY, session, settings, reference, start_date, end_date, scope, key
    )


@router.get("/latest", response_model=Headline)
def latest(session: DbSession, settings: AppSettings, reference: Reference) -> Headline:
    """The headline number with day/week/month changes and methodology status flags."""
    return IndexQueryService(session, settings, reference).headline()


@router.get("/sub-indices", response_model=SubIndices)
def sub_indices(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    date_: date | None = Query(None, alias="date"),
) -> SubIndices:
    """Purchase-window (T+1…T+45) and regional sub-indices for one day."""
    return IndexQueryService(session, settings, reference).sub_indices(date_)


@router.get("/daily/{day}/lineage", response_model=Lineage)
def lineage(day: date, session: DbSession, settings: AppSettings, reference: Reference) -> Lineage:
    """Audit trail: run parameters and every elementary aggregate behind the day's value."""
    return IndexQueryService(session, settings, reference).lineage(day)
