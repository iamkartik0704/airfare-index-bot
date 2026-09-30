"""The scrape worker process (doc 10 "Execution").

A pool of asyncio tasks bounded by ``worker.concurrency``. The loop:

1. recovers jobs whose lease expired (a crashed or killed worker),
2. claims up to the free capacity (atomic, per-source concurrency capped),
3. runs each claimed job through ``JobRunner``,
4. finalises sweeps whose jobs are all terminal.

``drain=True`` exits once the queue is empty — used for demos, backfills and
tests. SIGINT/SIGTERM stop claiming new work and let in-flight jobs finish.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import uuid
from dataclasses import dataclass, field

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.data_pipeline.evidence import EvidenceStore
from packages.domain.db import session_scope
from packages.domain.enums import JobStatus
from packages.domain.repositories.jobs import JobRepository
from packages.job_orchestration.runner import ClaimedJob, JobRunner
from packages.observability.logging import get_logger
from packages.observability.metrics import metrics
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory

log = get_logger("safar.worker")


@dataclass
class WorkerStats:
    processed: int = 0
    crashed: int = 0
    by_status: dict[str, int] = field(default_factory=dict)

    def add(self, status: JobStatus) -> None:
        self.processed += 1
        self.by_status[status.value] = self.by_status.get(status.value, 0) + 1


class Worker:
    def __init__(
        self,
        settings: Settings,
        reference: ReferenceData,
        *,
        fetchers: FetcherFactory | None = None,
        executor: ScrapeExecutor | None = None,
    ) -> None:
        self._settings = settings
        self._fetchers = fetchers or FetcherFactory(settings.scraping)
        executor = executor or ScrapeExecutor(self._fetchers, settings.scraping)
        self._runner = JobRunner(
            settings, reference, executor, EvidenceStore(settings.evidence_dir)
        )
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self._stop = asyncio.Event()

    def request_stop(self) -> None:
        self._stop.set()

    def _claim(self, limit: int) -> list[ClaimedJob]:
        with session_scope() as session:
            repo = JobRepository(session)
            recovered = repo.recover_expired_leases()
            if recovered:
                log.warning("worker.leases_recovered", count=recovered)
            jobs = repo.claim(
                worker_id=self.worker_id,
                limit=limit,
                lease_seconds=self._settings.worker.lease_seconds,
            )
            return [ClaimedJob.of(j) for j in jobs]

    def _housekeeping(self) -> None:
        with session_scope() as session:
            repo = JobRepository(session)
            repo.finalize_sweeps()
            for status, n in repo.status_counts().items():
                metrics.QUEUE_DEPTH.labels(status.value).set(n)

    async def run(self, *, drain: bool = False, max_jobs: int | None = None) -> WorkerStats:
        stats = WorkerStats()
        capacity = max(1, self._settings.worker.concurrency)
        in_flight: set[asyncio.Task[JobStatus]] = set()
        log.info("worker.started", worker_id=self.worker_id, concurrency=capacity, drain=drain)
        try:
            while not self._stop.is_set():
                budget = capacity - len(in_flight)
                if max_jobs is not None:
                    budget = min(budget, max_jobs - stats.processed - len(in_flight))
                claimed = await asyncio.to_thread(self._claim, budget) if budget > 0 else []
                for job in claimed:
                    in_flight.add(asyncio.create_task(self._runner.run(job)))
                if not in_flight:
                    await asyncio.to_thread(self._housekeeping)
                    if drain or (max_jobs is not None and stats.processed >= max_jobs):
                        break
                    await self._sleep(self._settings.worker.poll_interval_s)
                    continue
                done, in_flight = await asyncio.wait(
                    in_flight,
                    timeout=self._settings.worker.poll_interval_s,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    self._collect(task, stats)
        finally:
            if in_flight:
                await asyncio.wait(in_flight)
                for task in in_flight:
                    self._collect(task, stats)
            await asyncio.to_thread(self._housekeeping)
            await self._fetchers.aclose()
            log.info("worker.stopped", processed=stats.processed, by_status=stats.by_status)
        return stats

    @staticmethod
    def _collect(task: asyncio.Task[JobStatus], stats: WorkerStats) -> None:
        exc = task.exception()
        if exc is None:
            stats.add(task.result())
            return
        # A bug, not an expected failure: log loudly; the job's lease expires and it is retried.
        log.error("job.crashed", error_type=type(exc).__name__, error=str(exc), exc_info=exc)
        stats.crashed += 1

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except TimeoutError:
            return

    def install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.request_stop)
