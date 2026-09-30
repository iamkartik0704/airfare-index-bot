"""Execute one claimed scrape job end to end (doc 10 "Job Lifecycle").

    preflight (source enabled? circuit/block cooldown open?)
      → ScrapeExecutor.execute  (governed fetch + parse, bounded by job timeout)
      → persist evidence + raw quotes           ┐ one transaction
      → NormalizationPipeline.process_job       │
      → job SUCCESS / RETRY / FAILED / SKIPPED  │
      → circuit breaker + source health         ┘

Failure policy (doc 10 §4):

| error                         | job      | source                               |
|-------------------------------|----------|--------------------------------------|
| network / timeout / 5xx       | RETRY    | circuit failure                      |
| 429 rate limited              | RETRY after Retry-After | host paused by the limiter |
| block / CAPTCHA / 401 / 403   | FAILED   | BLOCKED for ``block_cooldown_s``     |
| parse error                   | FAILED (dead-letter) | circuit failure          |
| robots.txt disallow           | SKIPPED  | —                                    |
| circuit open / source disabled| SKIPPED  | —                                    |
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.data_pipeline.evidence import EvidenceStore
from packages.data_pipeline.pipeline import NormalizationPipeline
from packages.domain.db import session_scope
from packages.domain.enums import JobStatus, SourceStatus
from packages.domain.exceptions import SafarError
from packages.domain.models.database import ScrapeJob, Source, utcnow
from packages.domain.models.job import ScrapeContext
from packages.domain.repositories.health import HealthDelta, SourceHealthRepository
from packages.domain.repositories.jobs import JobRepository
from packages.domain.repositories.raw import RawStoreRepository
from packages.observability.logging import bind_context, get_logger
from packages.observability.metrics import metrics
from packages.scraping.core.exceptions import (
    CircuitOpenError,
    FetchTimeoutError,
    HttpStatusError,
    ParseError,
    RateLimitedError,
    RobotsDisallowedError,
    ScrapingError,
    SourceBlockedError,
    SourceDisabledError,
)
from packages.scraping.core.governance.blocking import detect_block
from packages.scraping.core.resilience.circuit_breaker import CircuitBreaker, CircuitSnapshot
from packages.scraping.engine import ScrapeExecutor, ScrapeOutcome
from packages.scraping.sources.base import BaseSourceAdapter
from packages.scraping.sources.registry import build_adapter

log = get_logger("safar.worker")


@dataclass(frozen=True)
class ClaimedJob:
    id: uuid.UUID
    source_id: str
    route_code: str
    origin: str
    destination: str
    travel_date: date
    purchase_window: int
    observation_date: date
    attempts: int

    @classmethod
    def of(cls, job: ScrapeJob) -> ClaimedJob:
        return cls(
            id=job.id,
            source_id=job.source_id,
            route_code=job.route.code,
            origin=job.route.origin_iata,
            destination=job.route.destination_iata,
            travel_date=job.travel_date,
            purchase_window=job.purchase_window,
            observation_date=job.observation_date,
            attempts=job.attempts,
        )


class JobRunner:
    def __init__(
        self,
        settings: Settings,
        reference: ReferenceData,
        executor: ScrapeExecutor,
        evidence: EvidenceStore,
    ) -> None:
        self._settings = settings
        self._executor = executor
        self._evidence = evidence
        self._pipeline = NormalizationPipeline(reference, settings.quality)
        self._adapters: dict[str, BaseSourceAdapter] = {}
        self._reference = reference
        self._breaker = CircuitBreaker(
            settings.scraping.circuit_failure_threshold, settings.scraping.circuit_cooldown_s
        )

    def _adapter(self, source_id: str) -> BaseSourceAdapter:
        if source_id not in self._adapters:
            self._adapters[source_id] = build_adapter(self._reference.source(source_id))
        return self._adapters[source_id]

    async def run(self, job: ClaimedJob) -> JobStatus:
        with bind_context(
            job_id=job.id,
            source=job.source_id,
            route=job.route_code,
            travel_date=job.travel_date,
            purchase_window=f"T+{job.purchase_window}",
            attempt=job.attempts,
        ):
            blocker = await asyncio.to_thread(self._preflight, job.id)
            if blocker is not None:
                return await self._finish_safely(job, None, blocker)
            adapter = self._adapter(job.source_id)
            context = ScrapeContext(
                source_id=job.source_id,
                origin=job.origin,
                destination=job.destination,
                travel_date=job.travel_date,
                purchase_window=job.purchase_window,
                observation_date=job.observation_date,
                job_id=job.id,
            )
            try:
                outcome = await asyncio.wait_for(
                    self._executor.execute(adapter, context),
                    timeout=self._settings.worker.job_timeout_s,
                )
            except TimeoutError:
                outcome = ScrapeOutcome(
                    source_id=job.source_id,
                    error=FetchTimeoutError("job exceeded its timeout", job_id=str(job.id)),
                )
            return await self._finish_safely(job, outcome, None)

    async def _finish_safely(
        self, job: ClaimedJob, outcome: ScrapeOutcome | None, blocker: ScrapingError | None
    ) -> JobStatus:
        """Persist the outcome; if the transaction itself fails, re-queue the job."""
        try:
            return await asyncio.to_thread(self._finish, job, outcome, blocker)
        except SafarError as exc:
            log.error("job.persist_failed", error_code=exc.code, error=str(exc))
            return await asyncio.to_thread(self._record_crash, job, exc)

    def _record_crash(self, claimed: ClaimedJob, error: SafarError) -> JobStatus:
        with session_scope() as session:
            job = session.get(ScrapeJob, claimed.id)
            if job is None:
                return JobStatus.FAILED
            status = JobRepository(session).mark_failure(
                job,
                code=error.code,
                message=str(error),
                retryable=error.retryable,
                retry_in=self._retry_delay(job),
            )
            metrics.SCRAPE_JOBS.labels(job.source_id, status.value.lower()).inc()
            return status

    # ------------------------------------------------------------------ helpers

    def _preflight(self, job_id: uuid.UUID) -> ScrapingError | None:
        with session_scope() as session:
            job = session.get(ScrapeJob, job_id)
            if job is None:
                return SourceDisabledError("job vanished", job_id=str(job_id))
            source = job.source
            if not source.enabled or source.status is SourceStatus.DISABLED:
                return SourceDisabledError("source is disabled", source=source.id)
            if source.circuit_open_until is not None and source.circuit_open_until > utcnow():
                until = f"{source.circuit_open_until:%H:%M}Z"
                return CircuitOpenError(
                    f"source {source.status.value.lower()} until {until}", source=source.id
                )
            return None

    def _finish(
        self, claimed: ClaimedJob, outcome: ScrapeOutcome | None, blocker: ScrapingError | None
    ) -> JobStatus:
        with session_scope() as session:
            job = session.get(ScrapeJob, claimed.id)
            assert job is not None
            jobs = JobRepository(session)
            health = SourceHealthRepository(session)
            delta = HealthDelta()
            if outcome is not None:
                self._store_evidence(session, job, outcome, delta)
            error = blocker or (outcome.error if outcome else None)

            if error is None and outcome is not None:
                report = self._pipeline.process_job(session, job)
                jobs.mark_success(job, items=len(outcome.quotes))
                delta.jobs_succeeded = 1
                delta.quotes_collected = len(outcome.quotes)
                delta.missing_fields = sum(report.missing_fields.values())
                self._circuit_success(health, job.source)
                status = JobStatus.SUCCESS
            else:
                assert error is not None
                status = self._handle_error(jobs, health, job, error, delta)
            health.record(job.source_id, delta)
            metrics.SCRAPE_JOBS.labels(job.source_id, status.value.lower()).inc()
            log.info(
                "job.finished",
                status=status.value,
                quotes=len(outcome.quotes) if outcome else 0,
                error_code=error.code if error else None,
                error=str(error) if error else None,
            )
            return status

    def _store_evidence(
        self, session: Session, job: ScrapeJob, outcome: ScrapeOutcome, delta: HealthDelta
    ) -> None:
        raw_repo = RawStoreRepository(session)
        response_ids: list[uuid.UUID] = []
        adapter = self._adapter(job.source_id)
        for response in outcome.responses:
            sha, uri = self._evidence.put(response.body)
            verdict = detect_block(response, adapter.block_markers)
            row = raw_repo.save_response(
                job,
                url=response.url,
                method=response.request.method,
                fetch_mode=response.fetch_mode,
                status_code=response.status,
                content_type=response.content_type,
                sha256=sha,
                byte_size=len(response.body),
                storage_uri=uri,
                duration_ms=response.elapsed_ms,
                fetched_at=response.fetched_at,
                blocked=verdict.blocked,
                block_reason=verdict.reason,
            )
            response_ids.append(row.id)
            delta.total_latency_ms += response.elapsed_ms
            code = str(response.status)
            delta.status_codes[code] = delta.status_codes.get(code, 0) + 1
        delta.requests = outcome.requests_sent
        raw_repo.save_quotes(
            [
                {
                    "job_id": job.id,
                    "response_id": response_ids[pq.response_index],
                    "source_id": job.source_id,
                    "route_id": job.route_id,
                    "observation_date": job.observation_date,
                    "travel_date": job.travel_date,
                    "purchase_window": job.purchase_window,
                    "observed_at": outcome.responses[pq.response_index].fetched_at,
                    "record_index": pq.record_index,
                    "raw_payload": pq.quote.to_payload(),
                    "parser_name": adapter.parser_name,
                    "parser_version": adapter.parser_version,
                    "created_at": utcnow(),
                }
                for pq in outcome.quotes
            ]
        )

    def _handle_error(
        self,
        jobs: JobRepository,
        health: SourceHealthRepository,
        job: ScrapeJob,
        error: ScrapingError,
        delta: HealthDelta,
    ) -> JobStatus:
        source = job.source
        message = str(error)
        if isinstance(error, (RobotsDisallowedError, CircuitOpenError, SourceDisabledError)):
            if isinstance(error, RobotsDisallowedError):
                delta.robots_denied = 1
            jobs.mark_skipped(job, code=error.code, message=message)
            return JobStatus.SKIPPED

        delta.jobs_failed = 1
        now = utcnow()
        if isinstance(error, SourceBlockedError):
            delta.blocked = 1
            until = now + timedelta(seconds=self._settings.scraping.block_cooldown_s)
            health.set_status(source, SourceStatus.BLOCKED, reason=message, open_until=until)
            metrics.SOURCE_UP.labels(source.id).set(0)
            return jobs.mark_failure(
                job, code=error.code, message=message, retryable=False, retry_in=0, now=now
            )
        if isinstance(error, RateLimitedError):
            delta.rate_limited = 1
            retry_in = error.retry_after_s or self._retry_delay(job)
            return jobs.mark_failure(
                job, code=error.code, message=message, retryable=True, retry_in=retry_in, now=now
            )
        if isinstance(error, ParseError):
            delta.parse_errors = 1
        self._circuit_failure(health, source, message)
        retryable = error.retryable and not (
            isinstance(error, HttpStatusError) and error.status < 500
        )
        return jobs.mark_failure(
            job,
            code=error.code,
            message=message,
            retryable=retryable,
            retry_in=self._retry_delay(job),
            now=now,
        )

    def _retry_delay(self, job: ScrapeJob) -> float:
        worker = self._settings.worker
        return min(
            worker.retry_base_delay_s * float(2 ** max(job.attempts - 1, 0)),
            worker.retry_max_delay_s,
        )

    def _circuit_success(self, health: SourceHealthRepository, source: Source) -> None:
        snap = self._breaker.record_success(
            CircuitSnapshot(source.consecutive_failures, source.circuit_open_until)
        )
        health.record_circuit(source, consecutive_failures=0, open_until=snap.open_until)
        source.last_success_at = utcnow()
        if source.status in (SourceStatus.DEGRADED, SourceStatus.BLOCKED):
            health.set_status(source, SourceStatus.ACTIVE, reason="recovered")
        metrics.SOURCE_UP.labels(source.id).set(1)

    def _circuit_failure(self, health: SourceHealthRepository, source: Source, reason: str) -> None:
        now = utcnow()
        before = CircuitSnapshot(source.consecutive_failures, source.circuit_open_until)
        after = self._breaker.record_failure(before, now)
        health.record_circuit(
            source, consecutive_failures=after.consecutive_failures, open_until=after.open_until
        )
        if after.open_until is not None and after.open_until > now:
            health.set_status(source, SourceStatus.DEGRADED, reason=f"circuit open: {reason}"[:500])
            metrics.SOURCE_UP.labels(source.id).set(0)
            log.warning("source.circuit_opened", failures=after.consecutive_failures)
