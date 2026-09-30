"""Database engine and unit-of-work helpers.

One engine per process, created from ``Settings.database_url``. Callers use
``session_scope()`` for a transactional unit of work: commit on success,
rollback on any exception, always close.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from packages.config.settings import get_settings
from packages.domain.exceptions import PersistenceError


def build_engine(url: str, **kwargs: Any) -> Engine:
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False, "timeout": 30})
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if ":memory:" not in url:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine
    kwargs.setdefault("pool_pre_ping", True)
    kwargs.setdefault("pool_size", 10)
    return create_engine(url, **kwargs)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def reset_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@contextmanager
def session_scope(factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    session = (factory or get_session_factory())()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise PersistenceError(f"database operation failed: {exc.__class__.__name__}") from exc
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
