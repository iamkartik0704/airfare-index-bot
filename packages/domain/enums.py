"""Enumerations shared by every subsystem (doc 06)."""

from __future__ import annotations

from enum import StrEnum


class SourceKind(StrEnum):
    AIRLINE = "AIRLINE"
    OTA = "OTA"
    SIMULATED = "SIMULATED"


class SourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"  # circuit open after repeated failures (doc 04)
    BLOCKED = "BLOCKED"  # challenge / CAPTCHA / 403 detected — we back off (doc 15)
    DISABLED = "DISABLED"  # switched off by an operator or policy


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRY = "RETRY"  # failed with a retryable error, waiting for `available_at`
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"  # terminal; the dead-letter set (doc 10) — re-queue manually
    SKIPPED = "SKIPPED"  # not executed by policy (robots, disabled source, open circuit)

    @property
    def is_terminal(self) -> bool:
        return self in {JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.SKIPPED}


class SweepTrigger(StrEnum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"
    BACKFILL = "BACKFILL"


class SweepStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"


class FetchMode(StrEnum):
    HTTP = "HTTP"
    BROWSER = "BROWSER"
    XHR = "XHR"  # JSON captured from a browser session's network traffic
    SIMULATED = "SIMULATED"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    SOLD_OUT = "SOLD_OUT"
    CANCELLED = "CANCELLED"


class QualityFlag(StrEnum):
    VALID = "VALID"
    OUTLIER = "OUTLIER"  # MAD / bounds check — quarantined (doc 07 phase 4)
    DUPLICATE = "DUPLICATE"  # superseded by a later observation of the same fare
    INVALID = "INVALID"  # failed validation (e.g. components do not sum to total)


class Cabin(StrEnum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"


class IndexFrequency(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class IndexScope(StrEnum):
    HEADLINE = "HEADLINE"
    WINDOW = "WINDOW"
    ROUTE = "ROUTE"
    REGION = "REGION"


class ImputationMethod(StrEnum):
    NONE = "NONE"
    LOCF = "LOCF"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
