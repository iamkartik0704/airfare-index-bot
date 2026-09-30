"""Centralised runtime settings.

Every deployment-specific value (database URL, credentials, hosts, schedules,
thresholds) is read from the environment here and nowhere else. Environment
variables use the ``SAFAR_`` prefix and ``__`` for nesting, e.g.
``SAFAR_SCRAPING__MAX_RETRIES=5``. See ``.env.example``.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.domain.exceptions import ConfigurationError

REPO_ROOT = Path(__file__).resolve().parents[2]
PURCHASE_WINDOWS: tuple[int, ...] = (1, 7, 15, 30, 45)


class ScrapingSettings(BaseModel):
    user_agent: str = "MoSPI-SAFAR-Bot/1.0 (+https://mospi.gov.in/safar)"
    robots_user_agent_token: str = "MoSPI-SAFAR-Bot"
    # If robots.txt cannot be fetched we do not scrape (doc 15: be conservative).
    robots_fail_closed: bool = True
    robots_cache_ttl_s: int = 6 * 3600
    request_timeout_s: float = 30.0
    max_retries: int = 3
    backoff_base_s: float = 2.0
    backoff_max_s: float = 120.0
    circuit_failure_threshold: int = 5
    circuit_cooldown_s: float = 1800.0
    # After a block/CAPTCHA the source is left alone this long before one trial request.
    block_cooldown_s: float = 6 * 3600.0
    browser_headless: bool = True
    # Optional, operator-supplied proxies for legitimate egress (doc 15). Empty = direct.
    proxies: list[SecretStr] = Field(default_factory=list)


class WorkerSettings(BaseModel):
    concurrency: int = 4
    lease_seconds: int = 300
    poll_interval_s: float = 2.0
    job_timeout_s: float = 240.0
    max_attempts: int = 3
    retry_base_delay_s: float = 60.0
    retry_max_delay_s: float = 3600.0
    metrics_port: int | None = None


class SchedulerSettings(BaseModel):
    timezone: str = "Asia/Kolkata"
    sweep_cron: str = "0 1 * * *"
    index_cron: str = "30 6 * * *"
    purchase_windows: tuple[int, ...] = PURCHASE_WINDOWS

    @field_validator("purchase_windows")
    @classmethod
    def _windows_positive(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value or any(w < 0 for w in value):
            raise ValueError("purchase_windows must be non-empty, non-negative day offsets")
        return tuple(sorted(set(value)))


class QualitySettings(BaseModel):
    mad_threshold: float = 3.5
    min_group_size_for_mad: int = 5
    fare_floor_inr: float = 500.0
    fare_ceiling_inr: float = 200_000.0
    total_tolerance_inr: float = 2.0


class IndexSettings(BaseModel):
    base_period_start: date | None = None
    base_period_end: date | None = None
    hedonic_adjustment: bool = True
    locf_max_days: int = 7
    min_quotes_per_cell: int = 1
    # Weight of each purchase window when collapsing window medians to a route
    # price. Empty → equal weights (no booking-curve weights are assumed).
    window_weights: dict[int, float] = Field(default_factory=dict)
    rolling_days: int = 7
    # The price basket: economy-cabin, non-stop fares (connections and premium
    # cabins are stored and analysable but do not enter the headline).
    cabins: tuple[str, ...] = ("ECONOMY",)
    include_connecting: bool = False

    @model_validator(mode="after")
    def _base_period_consistent(self) -> IndexSettings:
        start, end = self.base_period_start, self.base_period_end
        if (start is None) != (end is None):
            raise ValueError("base_period_start and base_period_end must be set together")
        if start and end and end < start:
            raise ValueError("base_period_end is before base_period_start")
        return self


class ApiSettings(BaseModel):
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    # Keys for the protected analyst endpoints (doc 11 `/api/v1/data/quotes`).
    api_keys: list[SecretStr] = Field(default_factory=list)
    default_page_size: int = 100
    max_page_size: int = 1000
    # Data older than this is reported stale (doc 13 alert: no quotes for >24 h + slack).
    stale_after_hours: int = 36


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAFAR_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = f"sqlite:///{REPO_ROOT / 'var' / 'safar.db'}"
    evidence_dir: Path = REPO_ROOT / "var" / "evidence"
    reference_dir: Path = REPO_ROOT / "packages" / "config" / "reference"
    log_level: str = "INFO"
    log_json: bool = True
    simulated_source_enabled: bool = False

    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.environment == "production":
            if self.database_url.startswith("sqlite"):
                raise ValueError("production requires a PostgreSQL SAFAR_DATABASE_URL")
            if not self.api.api_keys:
                raise ValueError("production requires SAFAR_API__API_KEYS for protected endpoints")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, validated once. Tests override via ``reset_settings``."""
    try:
        return Settings()
    except ValueError as exc:  # pydantic.ValidationError subclasses ValueError
        raise ConfigurationError(f"invalid configuration: {exc}") from exc


def reset_settings() -> None:
    get_settings.cache_clear()
