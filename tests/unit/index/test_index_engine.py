"""Index engine on deterministic synthetic datasets with hand-computed answers."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from packages.domain.enums import ImputationMethod, IndexFrequency, IndexScope
from packages.domain.models.index import IndexObservation, PriceCell
from packages.index_engine.aggregation.elementary import build_observations
from packages.index_engine.aggregation.periods import roll_up, rolling_mean
from packages.index_engine.analytics import lead_time_curve, sector_heatmap, weighted_window_fares
from packages.index_engine.backtesting import pearson, run_backtest, spearman
from packages.index_engine.engine import IndexConfig, IndexEngine
from packages.index_engine.exceptions import IndexCalculationError, InsufficientDataError
from packages.index_engine.methodology.imputation import impute_locf
from packages.index_engine.methodology.laspeyres import RoutePoint, laspeyres
from packages.index_engine.weighting.weights import IndexWeights

D = Decimal
BASE = date(2026, 9, 1)


def cell(day: date, route: str, window: int, fares: list[int], quality: float = 1.0) -> PriceCell:
    return PriceCell(
        observation_date=day,
        route_code=route,
        purchase_window=window,
        fares=tuple(D(f) for f in fares),
        quality_factors=tuple(D(str(quality)) for _ in fares),
        source_count=1,
    )


class TestLaspeyres:
    def test_weighted_relatives(self) -> None:
        # Ported from the original test: 10 % rise on both routes → 110.
        base = {"DEL-BOM": RoutePoint(D(5000), D(1)), "BOM-BLR": RoutePoint(D(4000), D(1))}
        now = {"DEL-BOM": RoutePoint(D(5500), D(1)), "BOM-BLR": RoutePoint(D(4400), D(1))}
        result = laspeyres(now, base, {"DEL-BOM": D("0.6"), "BOM-BLR": D("0.4")}, hedonic=True)
        assert result is not None and result.value == pytest.approx(D(110))

    def test_missing_base_route_renormalises_weights(self) -> None:
        base = {"DEL-BOM": RoutePoint(D(5000), D(1))}
        now = {"DEL-BOM": RoutePoint(D(5500), D(1)), "BOM-BLR": RoutePoint(D(4400), D(1))}
        result = laspeyres(now, base, {"DEL-BOM": D("0.6"), "BOM-BLR": D("0.4")}, hedonic=False)
        assert result is not None
        assert result.value == pytest.approx(D(110))
        assert result.weight_covered == D("0.6")

    def test_nothing_priced_returns_none_not_zero(self) -> None:
        assert laspeyres({}, {}, {"DEL-BOM": D(1)}, hedonic=True) is None

    def test_hedonic_term_removes_quality_mix_shift(self) -> None:
        # Price up 20 % entirely because travellers moved to a 20 %-better fare mix.
        base = {"R": RoutePoint(D(5000), D("1.0"))}
        now = {"R": RoutePoint(D(6000), D("1.2"))}
        result = laspeyres(now, base, {"R": D(1)}, hedonic=True)
        assert result is not None
        assert result.nominal == pytest.approx(D(120))
        assert result.value == pytest.approx(D(100))


class TestWeights:
    def test_normalised_and_equal_window_default(self) -> None:
        weights = IndexWeights.build({"A": D(3), "B": D(1)}, [1, 7])
        assert weights.routes == {"A": D("0.75"), "B": D("0.25")}
        assert weights.windows == {1: D("0.5"), 7: D("0.5")}

    def test_rejects_bad_weights(self) -> None:
        # Ported: zero weights used to silently produce 0.0.
        with pytest.raises(IndexCalculationError):
            IndexWeights.build({"A": D(0)}, [1])
        with pytest.raises(IndexCalculationError):
            IndexWeights.build({"A": D(1)}, [1], {9: 1.0})


class TestImputation:
    def test_locf_carries_forward_within_limit(self) -> None:
        # Ported: [100, None, None, 110, None, 120] → carried forward.
        days = [BASE + timedelta(days=i) for i in range(6)]
        prices = [100, None, None, 110, None, 120]
        obs = build_observations(
            [cell(d, "R", 1, [p]) for d, p in zip(days, prices, strict=True) if p is not None]
        )
        grid = impute_locf(obs, dates=days, cells=[("R", 1)], max_days=7)
        assert [grid[d][("R", 1)].median_fare for d in days] == [D(p) for p in (100, 100, 100, 110, 110, 120)]
        second = grid[days[1]][("R", 1)]
        assert second.imputed and second.imputation_method is ImputationMethod.LOCF
        assert second.imputed_from_date == days[0]

    def test_gap_beyond_limit_stays_missing(self) -> None:
        days = [BASE + timedelta(days=i) for i in range(5)]
        obs = build_observations([cell(days[0], "R", 1, [100])])
        grid = impute_locf(obs, dates=days, cells=[("R", 1)], max_days=2)
        assert ("R", 1) in grid[days[2]] and ("R", 1) not in grid[days[3]]


def two_route_series(days: int) -> list[PriceCell]:
    """R1 (weight 3) flat at 1000 then +10 % from day 7; R2 (weight 1) flat at 2000."""
    cells = []
    for i in range(days):
        day = BASE + timedelta(days=i)
        r1 = 1100 if i >= 7 else 1000
        for w in (1, 7):
            cells.append(cell(day, "R1", w, [r1 - 50, r1, r1 + 50]))
            cells.append(cell(day, "R2", w, [2000]))
    return cells


def engine(**config: object) -> IndexEngine:
    weights = IndexWeights.build({"R1": D(3), "R2": D(1)}, [1, 7], regions={"R1": "North", "R2": "South"})
    return IndexEngine(weights, IndexConfig(**config))  # type: ignore[arg-type]


class TestIndexEngine:
    def test_known_answer_headline_windows_regions_routes(self) -> None:
        result = engine().compute(two_route_series(10), date_from=BASE, date_to=BASE + timedelta(days=9))
        assert (result.base_start, result.base_end) == (BASE, BASE + timedelta(days=6))
        headline = {v.period_start: v.value for v in result.headline()}
        assert headline[BASE] == D(100)
        # R1 +10 % with weight 0.75 → 107.5
        assert headline[BASE + timedelta(days=8)] == D("107.5000")
        day8 = [v for v in result.daily if v.period_start == BASE + timedelta(days=8)]
        by = {(v.scope, v.scope_key): v.value for v in day8}
        assert by[(IndexScope.WINDOW, "T+1")] == D("107.5000")
        assert by[(IndexScope.REGION, "North")] == D("110.0000")
        assert by[(IndexScope.REGION, "South")] == D("100.0000")
        assert by[(IndexScope.ROUTE, "R1")] == D("110.0000")
        avg = next(v.avg_fare for v in day8 if v.scope is IndexScope.HEADLINE)
        assert avg == D("1325.00")  # 0.75*1100 + 0.25*2000

    def test_configured_base_period_and_period_rollups(self) -> None:
        result = engine(base_start=BASE + timedelta(days=7), base_end=BASE + timedelta(days=9)).compute(
            two_route_series(10), date_from=BASE, date_to=BASE + timedelta(days=9)
        )
        headline = {v.period_start: v.value for v in result.headline()}
        assert headline[BASE + timedelta(days=9)] == D(100)
        weekly = result.headline(IndexFrequency.WEEKLY)
        assert [w.period_start.weekday() for w in weekly] == [0] * len(weekly)
        monthly = result.headline(IndexFrequency.MONTHLY)
        assert len(monthly) == 1 and monthly[0].period_end == date(2026, 9, 30)
        daily_mean = sum(headline.values(), D(0)) / len(headline)
        assert monthly[0].value == daily_mean

    def test_missing_window_is_imputed_and_reported(self) -> None:
        cells = [c for c in two_route_series(10) if not (c.observation_date == BASE + timedelta(days=8) and c.route_code == "R2")]
        result = engine().compute(cells, date_from=BASE, date_to=BASE + timedelta(days=9))
        day8 = next(v for v in result.headline() if v.period_start == BASE + timedelta(days=8))
        assert day8.value == D("107.5000")  # R2 carried forward, index unaffected
        assert day8.imputed_share == D("0.5000") and day8.coverage_pct == D("50.00")

    def test_hedonic_adjustment_toggle(self) -> None:
        cells = []
        for i in range(8):
            day = BASE + timedelta(days=i)
            q = 1.2 if i == 7 else 1.0
            price = 1200 if i == 7 else 1000
            for w in (1, 7):
                cells.append(cell(day, "R1", w, [price], quality=q))
                cells.append(cell(day, "R2", w, [price], quality=q))
        last = BASE + timedelta(days=7)
        adj = engine(base_start=BASE, base_end=BASE).compute(cells, date_from=BASE, date_to=last)
        raw = engine(hedonic=False, base_start=BASE, base_end=BASE).compute(cells, date_from=BASE, date_to=last)
        assert adj.headline()[-1].value == D("100.0000")
        assert raw.headline()[-1].value == D("120.0000")
        assert adj.headline()[-1].nominal_value == D("120.0000")

    def test_no_data_raises(self) -> None:
        with pytest.raises(InsufficientDataError):
            engine().compute([], date_from=BASE, date_to=BASE)


def test_rollup_and_rolling_mean() -> None:
    result = engine().compute(two_route_series(14), date_from=BASE, date_to=BASE + timedelta(days=13))
    daily = [v for v in result.daily if v.scope is IndexScope.HEADLINE]
    assert roll_up(daily, IndexFrequency.DAILY) == daily
    assert rolling_mean([D(1), D(2), D(3)], 2) == [D(1), D("1.5"), D("2.5")]


class TestAnalytics:
    def test_lead_time_curve_and_elasticity(self) -> None:
        # fare = 10000 · days^-0.3 → elasticity −0.3
        fares = {w: D(str(round(10000 * w ** -0.3, 6))) for w in (1, 7, 15, 30, 45)}
        curve = lead_time_curve(fares)
        assert curve.elasticity == pytest.approx(-0.3, abs=1e-4)
        assert curve.cheapest_window == 45
        assert curve.points[0].premium_pct > 0 and curve.points[-1].premium_pct == 0

    def test_weighted_window_fares(self) -> None:
        medians = {("A", 1): D(100), ("B", 1): D(200), ("A", 7): D(50)}
        out = weighted_window_fares(medians, {"A": D("0.75"), "B": D("0.25")})
        assert out == {1: D("125.00"), 7: D("50.00")}

    def test_heatmap_changes(self) -> None:
        cells = sector_heatmap({"R": [("Aug", D(100)), ("Sep", D(110))]})
        assert cells[0].change_pct is None and cells[1].change_pct == D("10.00")


class TestBacktesting:
    def test_correlation_helpers(self) -> None:
        assert pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
        assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
        assert pearson([1, 2], [1, 2]) is None

    def test_thirty_days_three_months(self) -> None:
        daily = {}
        bench = {}
        for m, level in ((7, 5000), (8, 5500), (9, 6100)):
            start = date(2026, m, 1)
            bench[start] = D(level) * D("0.8")
            for i in range(28):
                daily[start + timedelta(days=i)] = (D(level), D(100))
        result = run_backtest(daily, bench, apix_synthetic=True, benchmark_synthetic=True, benchmark_label="test")
        m = result.metrics
        assert m["days_covered"] == 84 and m["months_covered"] == 3
        assert m["pearson"] == pytest.approx(1.0) and m["directional_accuracy"] == 1.0
        assert m["monthly_mape_pct"] == pytest.approx(25.0)
        assert result.verdict.startswith("PASS") and "SYNTHETIC" in result.verdict

    def test_insufficient_days(self) -> None:
        daily = {date(2026, 9, 1) + timedelta(days=i): (D(5000), None) for i in range(10)}
        result = run_backtest(
            daily, {date(2026, 9, 1): D(4000)}, apix_synthetic=False,
            benchmark_synthetic=False, benchmark_label="DGCA",
        )
        assert result.verdict.startswith("INSUFFICIENT")
        assert "SYNTHETIC" not in result.verdict


def test_observation_summary() -> None:
    [obs] = build_observations([cell(BASE, "R", 1, [300, 100, 200, 1000])])
    assert isinstance(obs, IndexObservation)
    assert (obs.median_fare, obs.min_fare, obs.max_fare, obs.quote_count) == (D("250.00"), D(100), D(1000), 4)
