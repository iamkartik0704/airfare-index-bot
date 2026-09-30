"""System console: health, sources, data freshness (doc 11 ``/api/v1/system/health``)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.dependencies.db import AppSettings, DbSession, Reference
from apps.api.schemas.operations import Freshness, HealthBucketOut, SourceHealthOut, SystemHealth
from apps.api.services.system_service import SystemService

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health", response_model=SystemHealth)
def system_health(session: DbSession, settings: AppSettings, reference: Reference) -> SystemHealth:
    """Engine status: blocked/degraded sources, data freshness, queue depth."""
    return SystemService(session, settings, reference).health()


@router.get("/sources", response_model=list[SourceHealthOut])
def sources(
    session: DbSession, settings: AppSettings, reference: Reference
) -> list[SourceHealthOut]:
    return SystemService(session, settings, reference).sources()


@router.get("/sources/{source_id}/health", response_model=list[HealthBucketOut])
def source_health(
    source_id: str,
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    hours: int = Query(48, ge=1, le=24 * 30),
) -> list[HealthBucketOut]:
    return SystemService(session, settings, reference).source_buckets(source_id, hours)


@router.get("/freshness", response_model=Freshness)
def freshness(session: DbSession, settings: AppSettings, reference: Reference) -> Freshness:
    return SystemService(session, settings, reference).freshness()
