"""Sector heatmap, carrier and channel analysis, cleaning funnel."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from apps.api.dependencies.db import AppSettings, DbSession
from apps.api.schemas.operations import CarrierAnalysis, ChannelAnalysis, FunnelOut, HeatmapOut
from apps.api.services.analytics_service import AnalyticsService
from packages.domain.enums import IndexFrequency

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
RouteQ = Query(None, pattern=r"^[A-Z]{3}-[A-Z]{3}$")


@router.get("/heatmap", response_model=HeatmapOut)
def heatmap(
    session: DbSession,
    settings: AppSettings,
    frequency: Literal["WEEKLY", "MONTHLY"] = "WEEKLY",
    periods: int = Query(8, ge=1, le=52),
) -> HeatmapOut:
    """Route × period index values with period-on-period change (sector heatmap)."""
    return AnalyticsService(session, settings).heatmap(IndexFrequency(frequency), periods)


@router.get("/carriers", response_model=CarrierAnalysis)
def carriers(
    session: DbSession,
    settings: AppSettings,
    date_: date | None = Query(None, alias="date"),
    route: str | None = RouteQ,
) -> CarrierAnalysis:
    return AnalyticsService(session, settings).carriers(date_, route)


@router.get("/channels", response_model=ChannelAnalysis)
def channels(
    session: DbSession, settings: AppSettings, date_: date | None = Query(None, alias="date")
) -> ChannelAnalysis:
    """Airline-direct vs OTA median fare for the same flights (convenience-fee wedge)."""
    return AnalyticsService(session, settings).channels(date_)


@router.get("/funnel", response_model=FunnelOut)
def funnel(
    session: DbSession,
    settings: AppSettings,
    date_: date | None = Query(None, alias="date"),
    route: str | None = RouteQ,
) -> FunnelOut:
    """Raw → normalized → valid → canonical counts for one observation date."""
    return AnalyticsService(session, settings).funnel(date_, route)
