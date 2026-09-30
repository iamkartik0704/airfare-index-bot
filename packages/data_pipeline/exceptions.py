"""Pipeline error types (validation, cleaning, normalization)."""

from __future__ import annotations

from packages.domain.exceptions import SafarError


class PipelineError(SafarError):
    code = "pipeline_error"


class CleaningError(PipelineError):
    """A displayed value could not be coerced (e.g. an amount with no digits)."""

    code = "cleaning_error"


class ValidationFailure(PipelineError):
    code = "validation_error"


class NormalizationError(PipelineError):
    """A value could not be mapped to the canonical vocabulary (e.g. unknown carrier)."""

    code = "normalization_error"
