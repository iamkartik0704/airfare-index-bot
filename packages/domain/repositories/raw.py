"""Immutable raw store: responses (evidence) and parsed raw quotes (doc 08)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from packages.domain.enums import FetchMode
from packages.domain.models.database import RawQuote, RawResponse, ScrapeJob
from packages.domain.repositories._upsert import upsert


class RawStoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_response(
        self,
        job: ScrapeJob,
        *,
        url: str,
        method: str,
        fetch_mode: FetchMode,
        status_code: int,
        content_type: str | None,
        sha256: str,
        byte_size: int,
        storage_uri: str,
        duration_ms: int,
        fetched_at: datetime,
        blocked: bool,
        block_reason: str | None,
    ) -> RawResponse:
        """Idempotent on (job, sha256): a retried job re-fetching identical bytes reuses the row."""
        upsert(
            self.session,
            RawResponse.__table__,  # type: ignore[arg-type]
            [
                {
                    "id": uuid.uuid4(),
                    "job_id": job.id,
                    "source_id": job.source_id,
                    "request_url": url,
                    "request_method": method,
                    "fetch_mode": fetch_mode.value,
                    "status_code": status_code,
                    "content_type": content_type,
                    "sha256": sha256,
                    "byte_size": byte_size,
                    "storage_uri": storage_uri,
                    "duration_ms": duration_ms,
                    "blocked": blocked,
                    "block_reason": block_reason,
                    "fetched_at": fetched_at,
                }
            ],
            conflict_columns=["job_id", "sha256"],
        )
        row = self.session.scalar(
            select(RawResponse).where(RawResponse.job_id == job.id, RawResponse.sha256 == sha256)
        )
        assert row is not None
        return row

    def save_quotes(self, rows: Sequence[dict[str, Any]]) -> None:
        for start in range(0, len(rows), 500):
            upsert(
                self.session,
                RawQuote.__table__,  # type: ignore[arg-type]
                rows[start : start + 500],
                conflict_columns=["response_id", "record_index", "parser_version"],
            )

    def latest_quotes_for_job(self, job_id: uuid.UUID) -> list[RawQuote]:
        """Raw quotes of a job from the newest parser version of each response."""
        latest = (
            select(RawQuote.response_id, func.max(RawQuote.parser_version).label("v"))
            .where(RawQuote.job_id == job_id)
            .group_by(RawQuote.response_id)
            .subquery()
        )
        stmt = (
            select(RawQuote)
            .join(
                latest,
                and_(
                    RawQuote.response_id == latest.c.response_id,
                    RawQuote.parser_version == latest.c.v,
                ),
            )
            .order_by(RawQuote.response_id, RawQuote.record_index)
        )
        return list(self.session.scalars(stmt))

    def responses_for_job(self, job_id: uuid.UUID) -> list[RawResponse]:
        return list(
            self.session.scalars(
                select(RawResponse)
                .where(RawResponse.job_id == job_id)
                .order_by(RawResponse.fetched_at)
            )
        )
