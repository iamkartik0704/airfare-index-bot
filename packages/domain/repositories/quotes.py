"""Canonical quote store (data access only; the rules live in ``packages.data_pipeline``)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Collection, Sequence
from datetime import date

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from packages.domain.enums import AvailabilityStatus, QualityFlag
from packages.domain.models.database import NormalizedQuote, Source


class NormalizedQuoteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def normalized_raw_ids(self, job_id: uuid.UUID) -> set[int]:
        return set(
            self.session.scalars(
                select(NormalizedQuote.raw_quote_id).where(NormalizedQuote.job_id == job_id)
            )
        )

    def delete_for_job(self, job_id: uuid.UUID) -> int:
        """Derived rows only — raw quotes and evidence are never deleted."""
        result = self.session.execute(
            delete(NormalizedQuote).where(NormalizedQuote.job_id == job_id)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    def live_by_dedup_key(self, keys: Collection[str]) -> dict[str, list[NormalizedQuote]]:
        found: dict[str, list[NormalizedQuote]] = defaultdict(list)
        if not keys:
            return found
        stmt = select(NormalizedQuote).where(
            NormalizedQuote.dedup_key.in_(list(keys)),
            NormalizedQuote.quality_flag != QualityFlag.DUPLICATE,
        )
        for row in self.session.scalars(stmt):
            found[row.dedup_key].append(row)
        return found

    def mark_duplicate(self, rows: Sequence[NormalizedQuote], reason: str) -> None:
        for row in rows:
            self.session.execute(
                update(NormalizedQuote)
                .where(NormalizedQuote.id == row.id)
                .values(
                    quality_flag=QualityFlag.DUPLICATE,
                    quality_reasons=[*row.quality_reasons, reason],
                    is_canonical=False,
                )
            )
        self.session.flush()

    def cell_rows(
        self, *, observation_date: date, route_id: int, purchase_window: int
    ) -> list[NormalizedQuote]:
        """Priced, live (VALID or OUTLIER) rows of one (date, route, window) cell."""
        return list(
            self.session.scalars(
                select(NormalizedQuote)
                .where(
                    NormalizedQuote.observation_date == observation_date,
                    NormalizedQuote.route_id == route_id,
                    NormalizedQuote.purchase_window == purchase_window,
                    NormalizedQuote.availability == AvailabilityStatus.AVAILABLE,
                    NormalizedQuote.total_fare.is_not(None),
                    NormalizedQuote.quality_flag.in_([QualityFlag.VALID, QualityFlag.OUTLIER]),
                )
                .order_by(NormalizedQuote.id)
            )
        )

    def group_members(
        self, group_keys: Collection[str]
    ) -> dict[str, list[tuple[NormalizedQuote, int]]]:
        """Rows per cross-channel group, with their source's channel priority."""
        groups: dict[str, list[tuple[NormalizedQuote, int]]] = defaultdict(list)
        if not group_keys:
            return groups
        stmt = (
            select(NormalizedQuote, Source.channel_priority)
            .join(Source, Source.id == NormalizedQuote.source_id)
            .where(NormalizedQuote.group_key.in_(list(group_keys)))
            .order_by(NormalizedQuote.id)
        )
        for row, priority in self.session.execute(stmt).all():
            groups[row.group_key].append((row, priority))
        return groups
