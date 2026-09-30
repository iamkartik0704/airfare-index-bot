"""Shared fixtures.

* ``migrated_template`` — one SQLite database migrated with Alembic per test
  session (the schema is only ever created by migrations);
* ``db`` — a private copy of it per test, wired into settings and the engine;
* ``settings`` / ``reference`` — isolated configuration for each test.

Set ``SAFAR_TEST_DATABASE_URL`` to a PostgreSQL URL to run the tests marked
``postgres`` against a real server.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData, get_reference_data, reset_reference_data
from packages.config.settings import Settings, get_settings, reset_settings
from packages.domain.db import get_session_factory, reset_engine
from tests.helpers import alembic_config


@pytest.fixture(scope="session")
def migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("template") / "template.db"
    command.upgrade(alembic_config(f"sqlite:///{path}"), "head")
    return path


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SAFAR_ENVIRONMENT", "test")
    monkeypatch.setenv("SAFAR_DATABASE_URL", f"sqlite:///{tmp_path / 'unused.db'}")
    monkeypatch.setenv("SAFAR_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("SAFAR_SIMULATED_SOURCE_ENABLED", "true")
    monkeypatch.setenv("SAFAR_LOG_JSON", "false")
    monkeypatch.setenv("SAFAR_SCRAPING__BACKOFF_BASE_S", "0")
    monkeypatch.setenv("SAFAR_WORKER__POLL_INTERVAL_S", "0.01")
    monkeypatch.setenv("SAFAR_WORKER__RETRY_BASE_DELAY_S", "0")
    reset_settings()
    reset_reference_data()
    reset_engine()
    yield
    reset_engine()
    reset_settings()
    reset_reference_data()


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def reference() -> ReferenceData:
    return get_reference_data()


@pytest.fixture
def db(migrated_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """URL of a fresh, fully migrated database for this test."""
    path = tmp_path / "safar.db"
    shutil.copy(migrated_template, path)
    url = f"sqlite:///{path}"
    monkeypatch.setenv("SAFAR_DATABASE_URL", url)
    reset_settings()
    reset_engine()
    return url


@pytest.fixture
def session(db: str) -> Iterator[Session]:
    sess = get_session_factory()()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    import os

    if os.environ.get("SAFAR_TEST_DATABASE_URL", "").startswith("postgresql"):
        return
    skip = pytest.mark.skip(reason="set SAFAR_TEST_DATABASE_URL=postgresql+psycopg://… to run")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)
