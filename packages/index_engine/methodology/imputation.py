"""Missing-cell imputation: Last Observation Carried Forward (doc 09 §2).

When a (route, window) cell has no observation on a day — scraper blocked,
flights sold out, source down — the most recent observation within
``max_days`` is carried forward and marked ``imputed`` with its source date.
Beyond ``max_days`` the cell stays missing and the engine drops the route for
that day (re-normalising weights), which is recorded as lower coverage.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from packages.domain.enums import ImputationMethod
from packages.domain.models.index import IndexObservation

CellKey = tuple[str, int]  # (route_code, purchase_window)


def impute_locf(
    observations: Iterable[IndexObservation],
    *,
    dates: Sequence[date],
    cells: Iterable[CellKey],
    max_days: int,
) -> dict[date, dict[CellKey, IndexObservation]]:
    """Return a complete-as-possible grid ``date → cell → observation``."""
    observed: dict[date, dict[CellKey, IndexObservation]] = {d: {} for d in dates}
    for obs in observations:
        if obs.observation_date in observed:
            observed[obs.observation_date][(obs.route_code, obs.purchase_window)] = obs

    grid: dict[date, dict[CellKey, IndexObservation]] = {d: dict(observed[d]) for d in dates}
    if max_days <= 0:
        return grid
    for cell in set(cells):
        last: IndexObservation | None = None
        for day in dates:
            current = observed[day].get(cell)
            if current is not None:
                last = current
                continue
            if last is None or (day - last.observation_date) > timedelta(days=max_days):
                continue
            grid[day][cell] = last.model_copy(
                update={
                    "observation_date": day,
                    "imputed": True,
                    "imputation_method": ImputationMethod.LOCF,
                    "imputed_from_date": last.observation_date,
                }
            )
    return grid
