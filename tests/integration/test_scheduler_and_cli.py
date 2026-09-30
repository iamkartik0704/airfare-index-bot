"""Scheduler slot idempotency / catch-up, and the ``safar`` CLI end to end."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.db import session_scope
from packages.domain.models.database import NormalizedQuote, ScrapeJob, Sweep
from packages.job_orchestration.cli import main
from packages.job_orchestration.scheduler import Scheduler, last_fire_time

IST = ZoneInfo("Asia/Kolkata")


def test_last_fire_time() -> None:
    trigger = CronTrigger.from_crontab("0 1 * * *", timezone=IST)
    assert last_fire_time(trigger, datetime(2026, 9, 30, 3, 0, tzinfo=IST)) == datetime(
        2026, 9, 30, 1, 0, tzinfo=IST
    )
    assert last_fire_time(trigger, datetime(2026, 9, 30, 0, 30, tzinfo=IST)) == datetime(
        2026, 9, 29, 1, 0, tzinfo=IST
    )


class TestScheduler:
    def test_repeated_and_late_fires_map_to_one_sweep(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        scheduler = Scheduler(settings, reference)
        fire = datetime(2026, 9, 30, 1, 0, tzinfo=IST)
        scheduler.run_sweep(fire)
        scheduler.run_sweep(fire)  # double fire / restart
        with session_scope() as session:
            assert session.scalar(select(func.count()).select_from(Sweep)) == 1
            assert session.scalar(select(func.count()).select_from(ScrapeJob)) == 240

    def test_catch_up_is_idempotent(self, db: str, settings: Settings, reference: ReferenceData) -> None:
        scheduler = Scheduler(settings, reference)
        scheduler.catch_up()
        scheduler.catch_up()
        with session_scope() as session:
            slots = list(session.scalars(select(Sweep.slot)))
        assert len(slots) == 1 and slots[0].startswith("scheduled:")

    def test_jobs_survive_failures_without_raising(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        scheduler = Scheduler(settings, reference)
        scheduler.run_index()  # no data yet: logged, recorded, not raised
        scheduler.housekeeping()


def _json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    out = capsys.readouterr().out
    return json.loads(out[out.index("{") :])


def test_cli_operator_flow(db: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["seed"]) == 0
    capsys.readouterr()
    # A route is priced only when all five purchase windows are observed.
    assert main(["sweep", "--date", "2026-09-30", "--route", "DEL-BOM"]) == 0
    assert _json(capsys)["jobs_enqueued"] == 10  # 5 windows × 2 simulated channels
    assert main(["worker", "--drain"]) == 0
    assert _json(capsys)["processed"] == 10
    assert main(["index"]) == 0
    assert _json(capsys)["daily_values"] > 0
    assert main(["status"]) == 0
    assert _json(capsys)["jobs"] == {"SUCCESS": 10}

    with session_scope() as session:
        job_id = str(session.scalars(select(ScrapeJob.id)).first())
        before = session.scalar(select(func.count()).select_from(NormalizedQuote))
    assert main(["replay", "--job", job_id]) == 0
    assert _json(capsys)["normalized"] > 0
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(NormalizedQuote)) == before

    assert main(["requeue", "--job", job_id]) == 0
    assert _json(capsys) == {"requeued": 1}


def test_cli_reports_typed_errors(db: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sweep", "--source", "indigo"]) == 1
    assert "configuration_error" in capsys.readouterr().err
    assert main(["backtest"]) == 1  # no benchmark loaded
    assert "insufficient_data" in capsys.readouterr().err
