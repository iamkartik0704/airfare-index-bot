"""``safar`` — operator CLI for the collection and index pipeline.

    safar seed                         sync reference data (basket, sources) into the DB
    safar sweep [--date D] [--source S …] [--route R …] [--window W …]
    safar backfill --start D --end D   simulated source only
    safar worker [--drain] [--max-jobs N]
    safar scheduler                    cron: sweeps 01:00 IST, index 06:30 IST
    safar index [--date-to D]          recompute the APIx series
    safar backtest                     compare APIx with the loaded DGCA benchmark
    safar requeue (--job ID … | --failed [--source S])
    safar replay --job ID              rebuild a job's normalized quotes from raw
    safar health-check [--source S …]  structural check of each adapter's source
    safar status                       queue and source summary
    safar demo [--days N]              seed + backfill + worker + index + backtest

Migrations are applied with ``alembic upgrade head`` (never at runtime).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, update

from packages.config.reference import get_reference_data
from packages.config.settings import Settings, get_settings
from packages.domain.db import session_scope
from packages.domain.enums import JobStatus, SweepTrigger
from packages.domain.exceptions import SafarError
from packages.domain.models.database import ScrapeJob, Source
from packages.domain.repositories.benchmarks import BenchmarkRepository
from packages.domain.repositories.jobs import JobRepository
from packages.domain.repositories.reference import sync_reference_data
from packages.index_engine.backtest_service import BacktestService
from packages.index_engine.service import IndexService
from packages.job_orchestration.scheduler import Scheduler
from packages.job_orchestration.sweep import SweepGenerator, backfill_slot, manual_slot
from packages.job_orchestration.worker import Worker
from packages.observability.logging import configure_logging


def _date(text: str) -> date:
    return date.fromisoformat(text)


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str))


def cmd_seed(settings: Settings, _: argparse.Namespace) -> None:
    with session_scope() as session:
        sync_reference_data(session, get_reference_data())
    _print({"seeded": True})


def cmd_sweep(settings: Settings, args: argparse.Namespace) -> None:
    with session_scope() as session:
        result = SweepGenerator(settings, get_reference_data()).create(
            session,
            observation_date=args.date or date.today(),
            slot=args.slot or manual_slot(),
            trigger=SweepTrigger.MANUAL,
            requested_by="cli",
            sources=args.source,
            routes=args.route,
            windows=tuple(args.window) if args.window else None,
        )
    _print(result.__dict__)


def cmd_backfill(settings: Settings, args: argparse.Namespace) -> None:
    results = []
    day = args.start
    while day <= args.end:
        with session_scope() as session:
            results.append(
                SweepGenerator(settings, get_reference_data()).create(
                    session,
                    observation_date=day,
                    slot=backfill_slot(day),
                    trigger=SweepTrigger.BACKFILL,
                    requested_by="cli",
                    sources=args.source,
                )
            )
        day += timedelta(days=1)
    _print({"sweeps": len(results), "jobs_enqueued": sum(r.jobs_enqueued for r in results)})


def cmd_worker(settings: Settings, args: argparse.Namespace) -> None:
    async def main() -> None:
        worker = Worker(settings, get_reference_data())
        worker.install_signal_handlers()
        stats = await worker.run(drain=args.drain, max_jobs=args.max_jobs)
        _print(stats.__dict__)

    if settings.worker.metrics_port:
        from prometheus_client import start_http_server

        from packages.observability.metrics.metrics import REGISTRY

        start_http_server(settings.worker.metrics_port, registry=REGISTRY)
    asyncio.run(main())


def cmd_scheduler(settings: Settings, _: argparse.Namespace) -> None:
    Scheduler(settings, get_reference_data()).start()


def cmd_index(settings: Settings, args: argparse.Namespace) -> None:
    with session_scope() as session:
        summary = IndexService(settings, get_reference_data()).compute(
            session, date_to=args.date_to
        )
    _print(summary.__dict__)


def cmd_backtest(settings: Settings, args: argparse.Namespace) -> None:
    with session_scope() as session:
        summary = BacktestService().run(session, date_from=args.date_from, date_to=args.date_to)
    _print(summary.__dict__)


def cmd_requeue(settings: Settings, args: argparse.Namespace) -> None:
    with session_scope() as session:
        ids: list[uuid.UUID] = [uuid.UUID(j) for j in args.job or []]
        if args.failed:
            stmt = select(ScrapeJob.id).where(ScrapeJob.status == JobStatus.FAILED)
            if args.source:
                stmt = stmt.where(ScrapeJob.source_id.in_(args.source))
            ids.extend(session.scalars(stmt))
        count = JobRepository(session).requeue(ids)
    _print({"requeued": count})


def cmd_replay(settings: Settings, args: argparse.Namespace) -> None:
    from packages.data_pipeline.pipeline import NormalizationPipeline

    pipeline = NormalizationPipeline(get_reference_data(), settings.quality)
    with session_scope() as session:
        job = session.get(ScrapeJob, uuid.UUID(args.job))
        if job is None:
            raise SafarError("job not found", job_id=args.job)
        report = pipeline.process_job(session, job, rebuild=True)
    _print(report.as_dict())


def cmd_health_check(settings: Settings, args: argparse.Namespace) -> None:
    from packages.scraping.engine import ScrapeExecutor
    from packages.scraping.fetchers import FetcherFactory
    from packages.scraping.sources.registry import ADAPTERS, build_adapter

    reference = get_reference_data()

    async def main() -> list[dict[str, Any]]:
        fetchers = FetcherFactory(settings.scraping)
        executor = ScrapeExecutor(fetchers, settings.scraping)
        out = []
        try:
            for source in reference.sources:
                if source.id not in ADAPTERS or (args.source and source.id not in args.source):
                    continue
                result = await executor.health_check(build_adapter(source))
                out.append(result.model_dump())
        finally:
            await fetchers.aclose()
        return out

    _print(asyncio.run(main()))


def cmd_status(settings: Settings, _: argparse.Namespace) -> None:
    with session_scope() as session:
        counts = JobRepository(session).status_counts()
        sources = [
            {"id": s.id, "status": s.status.value, "enabled": s.enabled, "reason": s.status_reason}
            for s in session.scalars(select(Source).order_by(Source.id))
        ]
    _print({"jobs": {k.value: v for k, v in counts.items()}, "sources": sources})


def cmd_demo(settings: Settings, args: argparse.Namespace) -> None:
    """One-shot synthetic demo: every step uses the production code paths."""
    if not settings.simulated_source_enabled:
        raise SafarError("demo needs SAFAR_SIMULATED_SOURCE_ENABLED=true")
    from packages.scraping.sources.simulated.benchmark import synthetic_monthly_benchmark

    reference = get_reference_data()
    end = args.end or date.today()
    start = end - timedelta(days=args.days - 1)
    with session_scope() as session:
        sync_reference_data(session, reference)
        session.execute(
            update(Source).where(Source.id.in_(["simulated", "simulated_ota"])).values(enabled=True)
        )
    cmd_backfill(
        settings, argparse.Namespace(start=start, end=end, source=["simulated", "simulated_ota"])
    )
    cmd_worker(settings, argparse.Namespace(drain=True, max_jobs=None))
    cmd_index(settings, argparse.Namespace(date_to=end))
    months = sorted(
        {start.replace(day=1) + timedelta(days=31 * i) for i in range(args.days // 28 + 2)}
    )
    with session_scope() as session:
        BenchmarkRepository(session).upsert(
            [r for r in synthetic_monthly_benchmark(reference, months) if r.period_month <= end]
        )
    cmd_backtest(settings, argparse.Namespace(date_from=start, date_to=end))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="safar", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed").set_defaults(func=cmd_seed)

    p = sub.add_parser("sweep")
    p.add_argument("--date", type=_date)
    p.add_argument("--slot")
    p.add_argument("--source", action="append")
    p.add_argument("--route", action="append")
    p.add_argument("--window", action="append", type=int)
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("backfill")
    p.add_argument("--start", type=_date, required=True)
    p.add_argument("--end", type=_date, required=True)
    p.add_argument("--source", action="append")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("worker")
    p.add_argument("--drain", action="store_true")
    p.add_argument("--max-jobs", type=int)
    p.set_defaults(func=cmd_worker)

    sub.add_parser("scheduler").set_defaults(func=cmd_scheduler)

    p = sub.add_parser("index")
    p.add_argument("--date-to", type=_date)
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("backtest")
    p.add_argument("--date-from", type=_date)
    p.add_argument("--date-to", type=_date)
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("requeue")
    p.add_argument("--job", action="append")
    p.add_argument("--failed", action="store_true")
    p.add_argument("--source", action="append")
    p.set_defaults(func=cmd_requeue)

    p = sub.add_parser("replay")
    p.add_argument("--job", required=True)
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("health-check")
    p.add_argument("--source", action="append")
    p.set_defaults(func=cmd_health_check)

    sub.add_parser("status").set_defaults(func=cmd_status)

    p = sub.add_parser("demo")
    p.add_argument("--days", type=int, default=35)
    p.add_argument("--end", type=_date)
    p.set_defaults(func=cmd_demo)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    try:
        args.func(settings, args)
    except SafarError as exc:
        print(f"error [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
