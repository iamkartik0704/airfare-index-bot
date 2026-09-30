"""Back-test results and the loaded benchmark (ps.md 30-day DGCA back-test)."""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.dependencies.db import AppSettings, DbSession, Reference
from apps.api.schemas.operations import BacktestOut, BenchmarkOut, Methodology
from apps.api.services.system_service import SystemService

router = APIRouter(prefix="/api/v1", tags=["validation"])


@router.get("/backtests/latest", response_model=BacktestOut)
def latest_backtest(session: DbSession, settings: AppSettings, reference: Reference) -> BacktestOut:
    return SystemService(session, settings, reference).latest_backtest()


@router.get("/benchmarks", response_model=list[BenchmarkOut])
def benchmarks(
    session: DbSession, settings: AppSettings, reference: Reference
) -> list[BenchmarkOut]:
    return SystemService(session, settings, reference).benchmarks()


@router.get("/methodology", response_model=Methodology)
def methodology(session: DbSession, settings: AppSettings, reference: Reference) -> Methodology:
    """Formula, basket, weights, fare classes and data-status flags behind the index."""
    return SystemService(session, settings, reference).methodology()
