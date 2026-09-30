"""Shared response shapes: pagination, errors, data-origin labelling."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
DataOrigin = Literal["live", "simulated", "mixed", "none"]


def data_origin(flags: Iterable[bool]) -> DataOrigin:
    """``simulated`` if every contributing row is synthetic, ``live`` if none are."""
    values = list(flags)
    if not values:
        return "none"
    if all(values):
        return "simulated"
    return "mixed" if any(values) else "live"


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
