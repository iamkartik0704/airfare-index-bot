"""Scrape job models (doc 06 ``ScrapeJob``, doc 10 job lifecycle)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import JobStatus


class ScrapeContext(BaseModel):
    """What one scrape task asks a source for (doc 05 ``build_requests(context)``)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    travel_date: date
    purchase_window: int = Field(ge=0)
    observation_date: date
    job_id: UUID | None = None
    adults: int = Field(default=1, ge=1, le=1)  # single adult economy fare, as in CPI pricing

    @property
    def route_code(self) -> str:
        return f"{self.origin}-{self.destination}"


class ScrapeJob(BaseModel):
    """Read model of a persisted job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sweep_id: UUID
    source_id: str
    route_code: str
    observation_date: date
    travel_date: date
    purchase_window: int
    status: JobStatus
    attempts: int
    max_attempts: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items_scraped: int = 0
    errors_encountered: int = 0
    last_error_code: str | None = None
    last_error_message: str | None = None
