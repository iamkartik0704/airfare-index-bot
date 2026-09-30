"""Liveness and readiness probes (for Docker / Kubernetes health checks)."""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.dependencies.db import DbSession
from apps.api.repositories.system_read import SystemReadRepository

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(session: DbSession) -> dict[str, str]:
    SystemReadRepository(session).ping()
    return {"status": "ok", "database": "ok"}
