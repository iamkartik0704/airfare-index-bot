"""raw_quotes → normalized_quotes for one scrape job (docs 03, 07).

    raw quote ─ clean ─ validate ─ normalize ─ dedup (latest wins)
                                        └─ outlier flags for the cell (MAD)
                                        └─ canonical representative per group

``process_job`` is idempotent: raw quotes already normalized are skipped, and
the outlier and canonical passes are pure recomputations. ``rebuild=True``
deletes the job's *derived* rows and regenerates them from the immutable raw
store (replay after a normalization fix, doc 07 phase 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.config.settings import QualitySettings
from packages.data_pipeline.deduplication.deduper import (
    CanonicalCandidate,
    choose_canonical,
    dedup_key,
    group_key,
)
from packages.data_pipeline.exceptions import NormalizationError
from packages.data_pipeline.models.report import PipelineReport
from packages.data_pipeline.normalization.normalizer import Normalizer, RawContext
from packages.data_pipeline.validation.outliers import detect_outliers
from packages.domain.enums import AvailabilityStatus, QualityFlag
from packages.domain.models.database import NormalizedQuote, RawQuote, ScrapeJob
from packages.domain.models.quote import AirfareQuote, RawFareQuote
from packages.domain.repositories.quotes import NormalizedQuoteRepository
from packages.domain.repositories.raw import RawStoreRepository
from packages.observability.logging import get_logger
from packages.observability.metrics import metrics

PIPELINE_VERSION = "1"
OUTLIER_REASONS = frozenset({"BELOW_FARE_FLOOR", "ABOVE_FARE_CEILING", "MAD_OUTLIER"})
OPTIONAL_COMPONENT_REASONS = {
    "BASE_FARE_MISSING": "base_fare",
    "TAXES_MISSING": "taxes",
    "AIRPORT_FEES_MISSING": "airport_fees",
    "CONVENIENCE_FEE_MISSING": "convenience_fee",
}

log = get_logger("safar.pipeline")


@dataclass
class _Candidate:
    raw: RawQuote
    quote: AirfareQuote
    dedup_key: str
    group_key: str
    duplicate_reason: str | None = None


class NormalizationPipeline:
    def __init__(self, reference: ReferenceData, quality: QualitySettings) -> None:
        self._normalizer = Normalizer(
            reference, total_tolerance=Decimal(str(quality.total_tolerance_inr))
        )
        self._quality = quality
        self._synthetic = {s.id: s.is_synthetic for s in reference.sources}

    def process_job(
        self, session: Session, job: ScrapeJob, *, rebuild: bool = False
    ) -> PipelineReport:
        report = PipelineReport()
        quotes = NormalizedQuoteRepository(session)
        if rebuild:
            quotes.delete_for_job(job.id)
            session.flush()
        raws = RawStoreRepository(session).latest_quotes_for_job(job.id)
        done = quotes.normalized_raw_ids(job.id)
        report.raw = len(raws)
        report.already_normalized = sum(1 for r in raws if r.id in done)

        candidates = self._normalize(job, [r for r in raws if r.id not in done], report)
        self._collapse_within_batch(candidates, report)
        self._supersede_existing(quotes, candidates, report)
        rows = [self._row(job, c) for c in candidates]
        session.add_all(rows)
        session.flush()
        report.normalized = len(rows)

        report.outliers = self._flag_outliers(quotes, job)
        self._choose_canonical(quotes, {c.group_key for c in candidates})
        for flag in QualityFlag:
            n = sum(1 for r in rows if r.quality_flag is flag)
            if n:
                metrics.PIPELINE_QUOTES.labels(flag.value).inc(n)
        for field_name, n in report.missing_fields.items():
            metrics.MISSING_FARE_FIELDS.labels(job.source_id, field_name).inc(n)
        log.info("pipeline.job_processed", **report.as_dict())
        return report

    # ------------------------------------------------------------------ stages

    def _normalize(
        self, job: ScrapeJob, raws: list[RawQuote], report: PipelineReport
    ) -> list[_Candidate]:
        route = job.route
        out: list[_Candidate] = []
        for raw in raws:
            ctx = RawContext(
                source_id=job.source_id,
                origin=route.origin_iata,
                destination=route.destination_iata,
                travel_date=job.travel_date,
                purchase_window=job.purchase_window,
                observation_date=job.observation_date,
                observed_at=raw.observed_at,
                is_synthetic=self._synthetic.get(job.source_id, False),
            )
            try:
                quote = self._normalizer.normalize(
                    RawFareQuote.model_validate(raw.raw_payload), ctx
                )
            except NormalizationError as exc:
                report.rejected[exc.message] += 1
                continue
            for reason in quote.quality_reasons:
                if reason in OPTIONAL_COMPONENT_REASONS:
                    report.missing_fields[OPTIONAL_COMPONENT_REASONS[reason]] += 1
            if quote.quality_flag is QualityFlag.INVALID:
                report.invalid += 1
            if quote.availability_status is AvailabilityStatus.SOLD_OUT:
                report.sold_out += 1
            elif quote.availability_status is AvailabilityStatus.CANCELLED:
                report.cancelled += 1
            out.append(
                _Candidate(
                    raw=raw,
                    quote=quote,
                    dedup_key=dedup_key(
                        quote.source_id,
                        quote.carrier,
                        quote.flight_number,
                        quote.fare_family or quote.fare_class,
                        quote.travel_date,
                        quote.observation_date,
                    ),
                    group_key=group_key(
                        quote.carrier,
                        quote.flight_number,
                        quote.fare_class,
                        quote.travel_date,
                        quote.observation_date,
                    ),
                )
            )
        return out

    @staticmethod
    def _collapse_within_batch(candidates: list[_Candidate], report: PipelineReport) -> None:
        latest: dict[str, _Candidate] = {}
        for cand in sorted(candidates, key=lambda c: (c.raw.observed_at, c.raw.id)):
            previous = latest.get(cand.dedup_key)
            if previous is not None:
                previous.duplicate_reason = "DUPLICATE_LISTING"
                report.duplicates += 1
            latest[cand.dedup_key] = cand

    @staticmethod
    def _supersede_existing(
        repo: NormalizedQuoteRepository, candidates: list[_Candidate], report: PipelineReport
    ) -> None:
        live = {c.dedup_key: c for c in candidates if c.duplicate_reason is None}
        existing = repo.live_by_dedup_key(live.keys())
        for key, rows in existing.items():
            newcomer = live[key]
            older = [r for r in rows if r.observed_at <= newcomer.raw.observed_at]
            if len(older) < len(rows):  # a newer observation already exists: the newcomer loses
                newcomer.duplicate_reason = "SUPERSEDED_BY_NEWER"
                report.superseded += 1
            elif older:
                repo.mark_duplicate(older, "SUPERSEDED")
                report.superseded += len(older)

    def _row(self, job: ScrapeJob, cand: _Candidate) -> NormalizedQuote:
        q = cand.quote
        flag = QualityFlag.DUPLICATE if cand.duplicate_reason else q.quality_flag
        reasons = [*q.quality_reasons, *([cand.duplicate_reason] if cand.duplicate_reason else [])]
        return NormalizedQuote(
            raw_quote_id=cand.raw.id,
            job_id=job.id,
            source_id=q.source_id,
            route_id=job.route_id,
            carrier_code=q.carrier,
            flight_number=q.flight_number,
            fare_class=q.fare_class,
            fare_family=q.fare_family[:64] if q.fare_family else None,
            cabin=q.cabin,
            observation_date=q.observation_date,
            observed_at=q.observed_at,
            travel_date=q.travel_date,
            departure_at=q.departure_at,
            purchase_window=q.purchase_window,
            advance_days=q.advance_purchase_days,
            base_fare=q.fares.base_fare,
            taxes=q.fares.taxes,
            airport_fees=q.fares.airport_fees,
            convenience_fee=q.fares.convenience_fee,
            total_fare=q.fares.total_fare,
            currency=q.currency,
            availability=q.availability_status,
            seats_left=q.seats_left,
            stops=q.stops,
            quality_factor=self._normalizer.quality_factor(q.fare_class),
            is_synthetic=q.is_synthetic,
            quality_flag=flag,
            quality_reasons=reasons,
            dedup_key=cand.dedup_key,
            group_key=cand.group_key,
            is_canonical=False,
            pipeline_version=PIPELINE_VERSION,
        )

    def _flag_outliers(self, repo: NormalizedQuoteRepository, job: ScrapeJob) -> int:
        rows = repo.cell_rows(
            observation_date=job.observation_date,
            route_id=job.route_id,
            purchase_window=job.purchase_window,
        )
        verdicts = detect_outliers(
            [r.total_fare for r in rows if r.total_fare is not None],
            threshold=self._quality.mad_threshold,
            min_group_size=self._quality.min_group_size_for_mad,
            floor=Decimal(str(self._quality.fare_floor_inr)),
            ceiling=Decimal(str(self._quality.fare_ceiling_inr)),
        )
        outliers = 0
        for row, reason in zip(rows, verdicts, strict=True):
            kept = [r for r in row.quality_reasons if r not in OUTLIER_REASONS]
            if reason is None:
                row.quality_flag, row.quality_reasons = QualityFlag.VALID, kept
            else:
                row.quality_flag, row.quality_reasons = QualityFlag.OUTLIER, [*kept, reason]
                outliers += 1
        repo.session.flush()
        return outliers

    @staticmethod
    def _choose_canonical(repo: NormalizedQuoteRepository, group_keys: set[str]) -> None:
        for members in repo.group_members(group_keys).values():
            winner = choose_canonical(
                [
                    CanonicalCandidate(
                        row.id, row.quality_flag, row.availability, prio, row.observed_at
                    )
                    for row, prio in members
                ]
            )
            for row, _ in members:
                row.is_canonical = row.id == winner
        repo.session.flush()
