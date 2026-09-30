"""Streaming exports of the canonical dataset and raw evidence (protected endpoints)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from collections.abc import Iterator
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.config.settings import Settings
from packages.data_pipeline.evidence import EvidenceStore
from packages.domain.exceptions import NotFoundError
from packages.domain.models.database import NormalizedQuote, RawQuote, RawResponse, Route

COLUMNS = (
    "id",
    "raw_quote_id",
    "response_id",
    "job_id",
    "source_id",
    "route",
    "carrier_code",
    "flight_number",
    "fare_class",
    "fare_family",
    "cabin",
    "observation_date",
    "observed_at",
    "travel_date",
    "purchase_window",
    "advance_days",
    "base_fare",
    "taxes",
    "airport_fees",
    "convenience_fee",
    "total_fare",
    "currency",
    "availability",
    "seats_left",
    "stops",
    "quality_flag",
    "quality_reasons",
    "is_canonical",
    "is_synthetic",
)


class ExportService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def _rows(self, day: date, canonical_only: bool) -> Iterator[dict[str, object]]:
        stmt = (
            select(NormalizedQuote, Route.code, RawQuote.response_id)
            .join(Route, Route.id == NormalizedQuote.route_id)
            .join(RawQuote, RawQuote.id == NormalizedQuote.raw_quote_id)
            .where(NormalizedQuote.observation_date == day)
            .order_by(NormalizedQuote.id)
        )
        if canonical_only:
            stmt = stmt.where(NormalizedQuote.is_canonical.is_(True))
        for quote, route, response_id in self.session.execute(stmt).yield_per(1000):
            row: dict[str, object] = {c: getattr(quote, c, None) for c in COLUMNS}
            row["route"] = route
            row["response_id"] = response_id
            row["quality_reasons"] = ";".join(quote.quality_reasons)
            yield row

    def quotes_csv(self, day: date, canonical_only: bool) -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
        writer.writeheader()
        yield buffer.getvalue()
        for row in self._rows(day, canonical_only):
            buffer.seek(0)
            buffer.truncate()
            writer.writerow({k: _plain(v) for k, v in row.items()})
            yield buffer.getvalue()

    def quotes_json(self, day: date, canonical_only: bool) -> Iterator[str]:
        yield "["
        first = True
        for row in self._rows(day, canonical_only):
            yield ("" if first else ",") + json.dumps({k: _plain(v) for k, v in row.items()})
            first = False
        yield "]"

    def evidence(self, response_id: uuid.UUID) -> tuple[bytes, str | None]:
        response = self.session.get(RawResponse, response_id)
        if response is None:
            raise NotFoundError("response not found", response_id=str(response_id))
        body = EvidenceStore(self.settings.evidence_dir).get(response.storage_uri)
        return body, response.content_type


def _plain(value: object) -> object:
    if value is None or isinstance(value, bool | int | str):
        return value
    if hasattr(value, "value"):  # enums
        return value.value
    return str(value)
