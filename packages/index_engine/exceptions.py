"""Index engine errors."""

from __future__ import annotations

from packages.domain.exceptions import SafarError


class IndexCalculationError(SafarError):
    code = "index_calculation_error"


class InsufficientDataError(IndexCalculationError):
    """Not enough observations to establish the base period or a value."""

    code = "insufficient_data"
