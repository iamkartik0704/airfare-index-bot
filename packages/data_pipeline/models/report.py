"""Pipeline run report — the per-job audit of the cleaning funnel."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineReport:
    raw: int = 0
    normalized: int = 0
    already_normalized: int = 0
    rejected: Counter[str] = field(default_factory=Counter)
    invalid: int = 0
    duplicates: int = 0
    superseded: int = 0
    outliers: int = 0
    sold_out: int = 0
    cancelled: int = 0
    missing_fields: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "already_normalized": self.already_normalized,
            "rejected": dict(self.rejected),
            "invalid": self.invalid,
            "duplicates": self.duplicates,
            "superseded": self.superseded,
            "outliers": self.outliers,
            "sold_out": self.sold_out,
            "cancelled": self.cancelled,
            "missing_fields": dict(self.missing_fields),
        }
