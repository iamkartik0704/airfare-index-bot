"""Basket weights (doc 09 "Weighting").

``W_r`` — route weights — come from the basket (``basket.yaml``: DGCA/PSD
passenger-traffic shares; currently INDICATIVE placeholders). Window weights
collapse the five advance-purchase medians into one route price; when not
configured they are equal (no booking-curve assumption is invented).
Weights are normalised to sum to 1 and snapshotted on every index run.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from packages.index_engine.exceptions import IndexCalculationError


@dataclass(frozen=True)
class IndexWeights:
    routes: Mapping[str, Decimal]
    windows: Mapping[int, Decimal]
    regions: Mapping[str, str]  # route code → region

    @classmethod
    def build(
        cls,
        route_weights: Mapping[str, Decimal],
        windows: Sequence[int],
        window_weights: Mapping[int, float] | None = None,
        regions: Mapping[str, str] | None = None,
    ) -> IndexWeights:
        if not route_weights:
            raise IndexCalculationError("basket has no routes")
        if any(w <= 0 for w in route_weights.values()):
            raise IndexCalculationError("route weights must be positive")
        total = sum(route_weights.values(), Decimal(0))
        routes = {code: w / total for code, w in route_weights.items()}

        if window_weights:
            unknown = set(window_weights) - set(windows)
            if unknown:
                raise IndexCalculationError(
                    "window weights for unknown windows", windows=sorted(unknown)
                )
            raw = {w: Decimal(str(window_weights.get(w, 0))) for w in windows}
        else:
            raw = {w: Decimal(1) for w in windows}
        if sum(raw.values()) <= 0:
            raise IndexCalculationError("window weights sum to zero")
        wtotal = sum(raw.values(), Decimal(0))
        return cls(
            routes=routes,
            windows={w: v / wtotal for w, v in raw.items() if v > 0},
            regions=dict(regions or {}),
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "routes": {k: str(v) for k, v in sorted(self.routes.items())},
            "windows": {str(k): str(v) for k, v in sorted(self.windows.items())},
        }
