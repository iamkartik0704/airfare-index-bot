"""The Airfare Price Index engine (doc 09).

A pure function from canonical price cells and weights to index values:

1. elementary aggregates — median fare per (date, route, window);
2. LOCF imputation of missing cells (bounded by ``locf_max_days``);
3. route price ``Pᵣ,d`` — window-weighted mean of the window medians; a route
   is priced on a day only when *every* basket window is available
   (observed or imputed), so the window mix cannot shift the route price;
4. base period prices ``Pᵣ,0`` / quality ``Q₀`` — means over the base period;
5. Laspeyres relatives with the hedonic quality term for the headline and
   for window (T+1 … T+45), region and route sub-indices;
6. weekly and monthly period averages.

No database, HTTP or scraper knowledge (doc 09 "Interface boundaries"), so
the same code runs in production, in backtests and in tests.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from packages.domain.enums import IndexFrequency, IndexScope
from packages.domain.models.index import IndexObservation, IndexValue, PriceCell
from packages.index_engine.aggregation.elementary import build_observations
from packages.index_engine.aggregation.periods import roll_up
from packages.index_engine.exceptions import InsufficientDataError
from packages.index_engine.methodology.imputation import CellKey, impute_locf
from packages.index_engine.methodology.laspeyres import RoutePoint, laspeyres
from packages.index_engine.weighting.weights import IndexWeights

FOUR = Decimal("0.0001")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class IndexConfig:
    hedonic: bool = True
    locf_max_days: int = 7
    min_quotes: int = 1
    base_start: date | None = None
    base_end: date | None = None
    #: When no base period is configured: the first N days on which the headline is priced.
    default_base_days: int = 7


@dataclass
class IndexComputation:
    base_start: date
    base_end: date
    observations: list[IndexObservation]
    daily: list[IndexValue]
    weekly: list[IndexValue]
    monthly: list[IndexValue]
    parameters: dict[str, Any] = field(default_factory=dict)

    def headline(self, frequency: IndexFrequency = IndexFrequency.DAILY) -> list[IndexValue]:
        series = {
            IndexFrequency.DAILY: self.daily,
            IndexFrequency.WEEKLY: self.weekly,
            IndexFrequency.MONTHLY: self.monthly,
        }[frequency]
        return [v for v in series if v.scope is IndexScope.HEADLINE]


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _mean_point(points: Sequence[RoutePoint]) -> RoutePoint:
    n = Decimal(len(points))
    return RoutePoint(
        price=sum((p.price for p in points), Decimal(0)) / n,
        quality=sum((p.quality for p in points), Decimal(0)) / n,
    )


class IndexEngine:
    def __init__(self, weights: IndexWeights, config: IndexConfig) -> None:
        self.weights = weights
        self.config = config

    # ------------------------------------------------------------------ grid

    def _route_point(self, cells: dict[CellKey, IndexObservation], route: str) -> RoutePoint | None:
        price = quality = Decimal(0)
        for window, share in self.weights.windows.items():
            obs = cells.get((route, window))
            if obs is None:
                return None
            price += share * obs.median_fare
            quality += share * obs.quality_factor
        return RoutePoint(price=price, quality=quality)

    def compute(
        self, cells: Iterable[PriceCell], *, date_from: date, date_to: date
    ) -> IndexComputation:
        observations = build_observations(cells, min_quotes=self.config.min_quotes)
        if not observations:
            raise InsufficientDataError("no priced cells to build an index from")
        first = min(o.observation_date for o in observations)
        dates = _days(min(first, date_from), date_to)
        all_cells = [(r, w) for r in self.weights.routes for w in self.weights.windows]
        grid = impute_locf(
            observations, dates=dates, cells=all_cells, max_days=self.config.locf_max_days
        )

        route_points = {
            d: {
                r: p
                for r in self.weights.routes
                if (p := self._route_point(grid[d], r)) is not None
            }
            for d in dates
        }
        base_start, base_end = self._base_period(dates, route_points)
        base_dates = [d for d in dates if base_start <= d <= base_end]

        def base_of(points_for: Callable[[date], dict[str, RoutePoint]]) -> dict[str, RoutePoint]:
            collected: dict[str, list[RoutePoint]] = {}
            for d in base_dates:
                for key, point in points_for(d).items():
                    collected.setdefault(key, []).append(point)
            return {k: _mean_point(v) for k, v in collected.items()}

        base_routes = base_of(lambda d: route_points[d])
        window_points = {
            w: {
                d: {
                    r: _cell_point(grid[d][(r, w)])
                    for r in self.weights.routes
                    if (r, w) in grid[d]
                }
                for d in dates
            }
            for w in self.weights.windows
        }

        def window_base(window: int) -> dict[str, RoutePoint]:
            return base_of(lambda d: window_points[window][d])

        base_windows = {w: window_base(w) for w in self.weights.windows}

        daily: list[IndexValue] = []
        for d in dates:
            if d < date_from:
                continue
            day_cells = grid[d]
            daily.extend(
                self._day_values(
                    d, day_cells, route_points[d], base_routes, window_points, base_windows
                )
            )

        emitted = [o for d in dates if d >= date_from for o in grid[d].values()]
        return IndexComputation(
            base_start=base_start,
            base_end=base_end,
            observations=emitted,
            daily=daily,
            weekly=roll_up(daily, IndexFrequency.WEEKLY),
            monthly=roll_up(daily, IndexFrequency.MONTHLY),
            parameters={
                "method": "laspeyres_fixed_basket",
                "hedonic_adjustment": self.config.hedonic,
                "locf_max_days": self.config.locf_max_days,
                "min_quotes_per_cell": self.config.min_quotes,
                "base_period": [base_start.isoformat(), base_end.isoformat()],
                "base_period_source": "configured"
                if self.config.base_start
                else "first_priced_days",
                "weights": self.weights.snapshot(),
            },
        )

    def _base_period(
        self, dates: Sequence[date], route_points: dict[date, dict[str, RoutePoint]]
    ) -> tuple[date, date]:
        if self.config.base_start and self.config.base_end:
            priced = [
                d
                for d in dates
                if self.config.base_start <= d <= self.config.base_end and route_points[d]
            ]
            if not priced:
                raise InsufficientDataError(
                    "no priced days in the configured base period",
                    base_start=self.config.base_start.isoformat(),
                    base_end=self.config.base_end.isoformat(),
                )
            return self.config.base_start, self.config.base_end
        priced = [d for d in dates if route_points[d]]
        if not priced:
            raise InsufficientDataError(
                "no day has a complete route price; cannot set a base period"
            )
        chosen = priced[: self.config.default_base_days]
        return chosen[0], chosen[-1]

    # ------------------------------------------------------------------ one day

    def _day_values(
        self,
        day: date,
        cells: dict[CellKey, IndexObservation],
        routes_now: dict[str, RoutePoint],
        base_routes: dict[str, RoutePoint],
        window_points: dict[int, dict[date, dict[str, RoutePoint]]],
        base_windows: dict[int, dict[str, RoutePoint]],
    ) -> list[IndexValue]:
        hedonic = self.config.hedonic
        weights = self.weights.routes
        out: list[IndexValue] = []

        def emit(scope: IndexScope, key: str, result: Any, used: Sequence[CellKey]) -> None:
            if result is None:
                return
            used_obs = [cells[c] for c in used if c in cells]
            total_cells = len(used) or 1
            observed = [o for o in used_obs if not o.imputed]
            out.append(
                IndexValue(
                    frequency=IndexFrequency.DAILY,
                    scope=scope,
                    scope_key=key,
                    period_start=day,
                    period_end=day,
                    value=result.value.quantize(FOUR),
                    nominal_value=result.nominal.quantize(FOUR),
                    avg_fare=result.avg_fare.quantize(CENT),
                    observation_count=sum(o.quote_count for o in observed),
                    coverage_pct=(Decimal(100) * len(observed) / total_cells).quantize(CENT),
                    imputed_share=(
                        Decimal(len(used_obs) - len(observed)) / len(used_obs)
                        if used_obs
                        else Decimal(0)
                    ).quantize(FOUR),
                    is_synthetic=any(o.is_synthetic for o in used_obs),
                )
            )

        windows = list(self.weights.windows)
        basket_cells = [(r, w) for r in weights for w in windows]
        emit(
            IndexScope.HEADLINE,
            "",
            laspeyres(routes_now, base_routes, weights, hedonic=hedonic),
            basket_cells,
        )
        for w in windows:
            emit(
                IndexScope.WINDOW,
                f"T+{w}",
                laspeyres(window_points[w][day], base_windows[w], weights, hedonic=hedonic),
                [(r, w) for r in weights],
            )
        for region in sorted(set(self.weights.regions.values())):
            members = {r: wt for r, wt in weights.items() if self.weights.regions.get(r) == region}
            emit(
                IndexScope.REGION,
                region,
                laspeyres(routes_now, base_routes, members, hedonic=hedonic),
                [(r, w) for r in members for w in windows],
            )
        for route in weights:
            emit(
                IndexScope.ROUTE,
                route,
                laspeyres(routes_now, base_routes, {route: Decimal(1)}, hedonic=hedonic),
                [(route, w) for w in windows],
            )
        return out


def _cell_point(obs: IndexObservation) -> RoutePoint:
    return RoutePoint(price=obs.median_fare, quality=obs.quality_factor)
