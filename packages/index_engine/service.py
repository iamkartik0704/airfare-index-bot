"""Index computation service: DB → pure engine → DB (doc 03 "Index Computation").

The engine always recomputes from the base period to ``date_to`` so weekly and
monthly averages are never built from partial re-runs, and every run stores
the exact weights, base period and parameters it used (auditability).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.enums import IndexScope, RunStatus
from packages.domain.repositories.index import IndexRepository
from packages.domain.repositories.reference import routes_by_code
from packages.index_engine.engine import IndexConfig, IndexEngine
from packages.index_engine.exceptions import IndexCalculationError, InsufficientDataError
from packages.index_engine.weighting.weights import IndexWeights
from packages.observability.logging import get_logger
from packages.observability.metrics import metrics

log = get_logger("safar.index")


@dataclass(frozen=True)
class IndexRunSummary:
    run_id: uuid.UUID
    date_from: date
    date_to: date
    base_start: date
    base_end: date
    daily_values: int
    latest_headline: Decimal | None


def build_engine(settings: Settings, reference: ReferenceData) -> IndexEngine:
    idx = settings.index
    weights = IndexWeights.build(
        {r.code: r.weight for r in reference.basket.routes},
        settings.scheduler.purchase_windows,
        idx.window_weights,
        {r.code: r.region for r in reference.basket.routes},
    )
    return IndexEngine(
        weights,
        IndexConfig(
            hedonic=idx.hedonic_adjustment,
            locf_max_days=idx.locf_max_days,
            min_quotes=idx.min_quotes_per_cell,
            base_start=idx.base_period_start,
            base_end=idx.base_period_end,
        ),
    )


class IndexService:
    def __init__(self, settings: Settings, reference: ReferenceData) -> None:
        self._settings = settings
        self._reference = reference
        self._engine = build_engine(settings, reference)

    def compute(self, session: Session, *, date_to: date | None = None) -> IndexRunSummary:
        repo = IndexRepository(session)
        earliest, latest = repo.observation_date_bounds()
        if earliest is None or latest is None:
            raise InsufficientDataError("no canonical quotes stored yet")
        date_to = date_to or latest
        configured = self._settings.index.base_period_start
        date_from = min(configured, earliest) if configured else earliest

        run = repo.start_run(date_from, date_to)
        run_id = run.id
        try:
            cells = repo.canonical_cells(
                date_from,
                date_to,
                cabins=self._settings.index.cabins,
                include_connecting=self._settings.index.include_connecting,
            )
            result = self._engine.compute(cells, date_from=date_from, date_to=date_to)
            route_ids = {
                code: r.id for code, r in routes_by_code(session, active_only=False).items()
            }
            repo.upsert_observations(run_id, result.observations, route_ids)
            repo.upsert_values(run_id, [*result.daily, *result.weekly, *result.monthly])
            parameters = {
                **result.parameters,
                "basket_version": self._reference.basket.version,
                "basket_status": self._reference.basket.status,
                "fare_class_status": self._reference.fare_classes.status,
                "quality_factors": {
                    c.code: str(c.quality_factor) for c in self._reference.fare_classes.classes
                },
                "cabins": list(self._settings.index.cabins),
                "include_connecting": self._settings.index.include_connecting,
            }
            repo.finish_run(
                run,
                status=RunStatus.SUCCESS,
                parameters=parameters,
                base_period=(result.base_start, result.base_end),
            )
        except IndexCalculationError as exc:
            # Discard partial results, but keep an auditable record of the failed run.
            session.rollback()
            failed = repo.start_run(date_from, date_to)
            repo.finish_run(failed, status=RunStatus.FAILED, error=str(exc))
            session.commit()
            metrics.INDEX_RUNS.labels("failed").inc()
            log.error("index.failed", error=str(exc))
            raise

        headline = [v for v in result.daily if v.scope is IndexScope.HEADLINE]
        latest_value = headline[-1].value if headline else None
        if headline:
            metrics.INDEX_VALUE.set(float(headline[-1].value))
            metrics.ROUTE_COVERAGE.set(float(headline[-1].coverage_pct) / 100)
        metrics.INDEX_RUNS.labels("success").inc()
        log.info(
            "index.computed",
            run_id=str(run_id),
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            base=f"{result.base_start}..{result.base_end}",
            latest=str(latest_value),
        )
        return IndexRunSummary(
            run_id=run_id,
            date_from=date_from,
            date_to=date_to,
            base_start=result.base_start,
            base_end=result.base_end,
            daily_values=len(result.daily),
            latest_headline=latest_value,
        )
