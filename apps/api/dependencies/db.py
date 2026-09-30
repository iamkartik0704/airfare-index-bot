"""Request-scoped dependencies: database session, settings, reference data, API key."""

from __future__ import annotations

import hmac
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData, get_reference_data
from packages.config.settings import Settings, get_settings
from packages.domain.db import get_session_factory
from packages.domain.exceptions import PersistenceError, SafarError


def get_db() -> Iterator[Session]:
    """One session per request; committed if the handler succeeds."""
    session = get_session_factory()()
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


class UnauthorizedError(SafarError):
    code = "unauthorized"


def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Protects analyst/operator endpoints (doc 11). Constant-time comparison."""
    keys = [k.get_secret_value() for k in settings.api.api_keys]
    if not keys:
        if settings.environment == "development":
            return  # local development without keys configured
        raise UnauthorizedError("API keys are not configured on this server")
    if x_api_key is None or not any(hmac.compare_digest(x_api_key, k) for k in keys):
        raise UnauthorizedError("missing or invalid X-API-Key")


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Reference = Annotated[ReferenceData, Depends(get_reference_data)]
ApiKey = Depends(require_api_key)
