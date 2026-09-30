"""Scrape jobs and sweeps; manual sweeps and dead-letter re-queue are protected."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from apps.api.dependencies.db import ApiKey, AppSettings, DbSession, Reference
from apps.api.schemas.common import Page
from apps.api.schemas.operations import JobOut, RequeueResult, SweepCreated, SweepOut, SweepRequest
from apps.api.services.system_service import SystemService
from packages.domain.enums import JobStatus, SweepStatus

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/jobs", response_model=Page[JobOut])
def jobs(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    status_: JobStatus | None = Query(None, alias="status"),
    source: str | None = Query(None, max_length=32),
    sweep_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[JobOut]:
    return SystemService(session, settings, reference).jobs(
        status_, source, sweep_id, limit, offset
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
def job(
    job_id: uuid.UUID, session: DbSession, settings: AppSettings, reference: Reference
) -> JobOut:
    return SystemService(session, settings, reference).job(job_id)


@router.post("/jobs/{job_id}/requeue", response_model=RequeueResult, dependencies=[ApiKey])
def requeue(
    job_id: uuid.UUID, session: DbSession, settings: AppSettings, reference: Reference
) -> RequeueResult:
    """Manual re-run of a terminal (FAILED / SKIPPED / SUCCESS) job."""
    return SystemService(session, settings, reference).requeue([job_id])


@router.get("/sweeps", response_model=Page[SweepOut])
def sweeps(
    session: DbSession,
    settings: AppSettings,
    reference: Reference,
    status_: SweepStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[SweepOut]:
    return SystemService(session, settings, reference).sweeps(status_, limit, offset)


@router.post(
    "/sweeps",
    response_model=SweepCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[ApiKey],
)
def create_sweep(
    request: SweepRequest, session: DbSession, settings: AppSettings, reference: Reference
) -> SweepCreated:
    """Enqueue a manual sweep; workers pick the jobs up asynchronously."""
    return SystemService(session, settings, reference).create_sweep(request)
