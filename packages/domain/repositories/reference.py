"""Synchronise reference data (YAML) into the relational tables."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.domain.models.database import Airport, Carrier, Route, Source, utcnow
from packages.domain.repositories._upsert import upsert


def sync_reference_data(session: Session, reference: ReferenceData) -> None:
    """Idempotent. Runtime state on ``sources`` (status, circuit) is never overwritten."""
    now = utcnow()
    upsert(
        session,
        Airport.__table__,  # type: ignore[arg-type]
        [{"code": a.code, "city": a.city, "name": a.name} for a in reference.basket.airports],
        conflict_columns=["code"],
        update_columns=["city", "name"],
    )
    upsert(
        session,
        Carrier.__table__,  # type: ignore[arg-type]
        [{"code": c.code, "name": c.name, "group": c.group} for c in reference.carriers],
        conflict_columns=["code"],
        update_columns=["name", "group"],
    )
    basket = reference.basket
    upsert(
        session,
        Route.__table__,  # type: ignore[arg-type]
        [
            {
                "code": r.code,
                "origin_iata": r.origin,
                "destination_iata": r.destination,
                "distance_km": r.distance_km,
                "region": r.region,
                "dgca_weight": r.weight,
                "basket_version": basket.version,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
            for r in basket.routes
        ],
        conflict_columns=["code"],
        update_columns=[
            "distance_km",
            "region",
            "dgca_weight",
            "basket_version",
            "active",
            "updated_at",
        ],
    )
    session.execute(
        update(Route)
        .where(Route.code.not_in([r.code for r in basket.routes]))
        .values(active=False, updated_at=now)
    )
    config_columns = [
        "name",
        "kind",
        "base_url",
        "carrier_code",
        "fetch_mode",
        "enabled",
        "is_synthetic",
        "tos_reviewed",
        "rate_limit_rpm",
        "max_concurrency",
        "crawl_delay_s",
        "channel",
        "channel_priority",
        "updated_at",
    ]
    upsert(
        session,
        Source.__table__,  # type: ignore[arg-type]
        [
            {
                "id": s.id,
                "name": s.name,
                "kind": s.kind.value,
                "base_url": s.base_url,
                "carrier_code": s.carrier,
                "fetch_mode": s.fetch_mode,
                "enabled": s.enabled,
                "is_synthetic": s.is_synthetic,
                "tos_reviewed": s.tos_reviewed,
                "rate_limit_rpm": s.rate_limit_rpm,
                "max_concurrency": s.max_concurrency,
                "crawl_delay_s": s.crawl_delay_s,
                "channel": s.channel,
                "channel_priority": s.channel_priority,
                "status": "ACTIVE",
                "consecutive_failures": 0,
                "created_at": now,
                "updated_at": now,
            }
            for s in reference.sources
        ],
        conflict_columns=["id"],
        update_columns=config_columns,
    )
    session.flush()


def routes_by_code(session: Session, *, active_only: bool = True) -> dict[str, Route]:
    stmt = select(Route)
    if active_only:
        stmt = stmt.where(Route.active.is_(True))
    return {r.code: r for r in session.scalars(stmt)}
