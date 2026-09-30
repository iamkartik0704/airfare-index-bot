"""Back-test service: stored APIx series + stored DGCA benchmark → stored result."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from packages.domain.repositories.benchmarks import BenchmarkRepository
from packages.index_engine.backtesting import run_backtest
from packages.index_engine.exceptions import InsufficientDataError
from packages.observability.logging import get_logger

log = get_logger("safar.backtest")


@dataclass(frozen=True)
class BacktestSummary:
    run_id: uuid.UUID
    verdict: str
    days_covered: int


class BacktestService:
    def run(
        self, session: Session, *, date_from: date | None = None, date_to: date | None = None
    ) -> BacktestSummary:
        repo = BenchmarkRepository(session)
        bench_rows = repo.monthly("ALL")
        if not bench_rows:
            raise InsufficientDataError(
                "no DGCA benchmark loaded; run scripts/db/load_dgca_benchmark.py <csv>"
            )
        date_from = date_from or date(1900, 1, 1)
        date_to = date_to or date(2999, 12, 31)
        daily_rows = repo.daily_headline(date_from, date_to)
        if not daily_rows:
            raise InsufficientDataError(
                "no daily index values to back-test; compute the index first"
            )

        labels = sorted({b.source_label for b in bench_rows})
        label = "; ".join(labels)
        bench_synthetic = any(b.is_synthetic for b in bench_rows)
        apix_synthetic = any(r.is_synthetic for r in daily_rows)
        result = run_backtest(
            {r.period_start: (r.avg_fare, r.value) for r in daily_rows},
            {b.period_month: b.avg_fare for b in bench_rows},
            apix_synthetic=apix_synthetic,
            benchmark_synthetic=bench_synthetic,
            benchmark_label=label,
        )
        if not result.points:
            raise InsufficientDataError("benchmark months do not overlap the index series")
        days = [p.period for p in result.points if p.granularity == "DAY"]
        run = repo.save_run(
            period=(
                min(days) if days else daily_rows[0].period_start,
                max(days) if days else daily_rows[-1].period_start,
            ),
            days_covered=int(result.metrics["days_covered"]),
            benchmark_label=label,
            benchmark_is_synthetic=bench_synthetic,
            apix_is_synthetic=apix_synthetic,
            metrics=result.metrics,
            verdict=result.verdict,
            points=[
                {
                    "granularity": p.granularity,
                    "period": p.period,
                    "apix_avg_fare": p.apix_avg_fare,
                    "apix_index": p.apix_index,
                    "benchmark_avg_fare": p.benchmark_avg_fare,
                    "abs_pct_error": p.abs_pct_error,
                }
                for p in result.points
            ],
        )
        log.info(
            "backtest.completed",
            verdict=result.verdict,
            **{k: v for k, v in result.metrics.items() if isinstance(v, int | float) or v is None},
        )
        return BacktestSummary(run.id, result.verdict, int(result.metrics["days_covered"]))
