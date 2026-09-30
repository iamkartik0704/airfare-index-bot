"""Typed loaders for the reference data under ``packages/config/reference/``.

The route basket, weights, sources, carriers and fare-class taxonomy are data,
not code: they come from DGCA/NSO releases and are refreshed on those
schedules. Each YAML file carries a ``status`` so that indicative placeholder
values are never silently mistaken for official ones.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from packages.config.settings import get_settings
from packages.domain.enums import SourceKind
from packages.domain.exceptions import ConfigurationError

DataStatus = Literal["OFFICIAL", "INDICATIVE"]
FetchMode = Literal["http", "browser", "simulated"]


class AirportDef(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{3}$")
    city: str
    name: str


class RouteDef(BaseModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    distance_km: int = Field(gt=0)
    region: str
    weight: Decimal = Field(gt=0)

    @property
    def code(self) -> str:
        return f"{self.origin}-{self.destination}"

    @model_validator(mode="after")
    def _distinct_endpoints(self) -> RouteDef:
        if self.origin == self.destination:
            raise ValueError(f"route {self.code} has identical endpoints")
        return self


class Basket(BaseModel):
    version: str
    status: DataStatus
    weights_source: str
    effective_from: str
    airports: list[AirportDef]
    routes: list[RouteDef]

    @model_validator(mode="after")
    def _routes_reference_airports(self) -> Basket:
        known = {a.code for a in self.airports}
        seen: set[str] = set()
        for route in self.routes:
            for code in (route.origin, route.destination):
                if code not in known:
                    raise ValueError(f"route {route.code} references unknown airport {code}")
            if route.code in seen:
                raise ValueError(f"duplicate route {route.code}")
            seen.add(route.code)
        return self

    def normalized_weights(self) -> dict[str, Decimal]:
        total = sum((r.weight for r in self.routes), Decimal(0))
        return {r.code: r.weight / total for r in self.routes}


class CarrierDef(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9]{2}$")
    name: str
    group: Literal["LCC", "FSC"]
    aliases: list[str] = Field(default_factory=list)


class FareClassDef(BaseModel):
    code: str
    label: str
    cabin: Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS"]
    quality_factor: Decimal = Field(gt=0)
    aliases: list[str] = Field(default_factory=list)


class FareClassTaxonomy(BaseModel):
    status: DataStatus
    note: str
    default_class: str
    classes: list[FareClassDef]

    @model_validator(mode="after")
    def _default_exists(self) -> FareClassTaxonomy:
        if self.default_class not in {c.code for c in self.classes}:
            raise ValueError(f"default_class {self.default_class} is not defined")
        return self


class SourceDef(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    kind: SourceKind
    base_url: str
    carrier: str | None = None
    fetch_mode: FetchMode
    enabled: bool = False
    is_synthetic: bool = False
    rate_limit_rpm: int = Field(gt=0)
    max_concurrency: int = Field(default=1, ge=1, le=3)
    crawl_delay_s: float = Field(default=0.0, ge=0)
    #: Distribution channel: airline "direct" sale or an "ota". Derived from ``kind``
    #: for real sources; the simulator declares which channel it imitates.
    channel: Literal["direct", "ota"] | None = None
    # Lower = preferred representative for cross-channel duplicates (doc 07).
    channel_priority: int = 10
    tos_reviewed: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _derive_channel(self) -> SourceDef:
        if self.channel is None:
            if self.kind is SourceKind.SIMULATED:
                raise ValueError(f"simulated source {self.id} must declare its channel")
            self.channel = "ota" if self.kind is SourceKind.OTA else "direct"
        return self

    @field_validator("base_url")
    @classmethod
    def _https(cls, value: str) -> str:
        if not value.startswith(("https://", "sim://")):
            raise ValueError("source base_url must be https:// (or sim:// for the simulator)")
        return value


class ReferenceData(BaseModel):
    basket: Basket
    carriers: list[CarrierDef]
    fare_classes: FareClassTaxonomy
    sources: list[SourceDef]

    def source(self, source_id: str) -> SourceDef:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise ConfigurationError("unknown source", source=source_id)

    def carrier_alias_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for carrier in self.carriers:
            for alias in [carrier.code, carrier.name, *carrier.aliases]:
                mapping[alias.strip().upper()] = carrier.code
        return mapping


def _read_yaml(path: Path) -> object:
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise ConfigurationError("reference file missing", path=str(path)) from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"reference file is not valid YAML: {exc}", path=str(path)
        ) from exc


def load_reference_data(directory: Path) -> ReferenceData:
    try:
        return ReferenceData(
            basket=Basket.model_validate(_read_yaml(directory / "basket.yaml")),
            carriers=[
                CarrierDef.model_validate(c)
                for c in _as_list(_read_yaml(directory / "carriers.yaml"), "carriers")
            ],
            fare_classes=FareClassTaxonomy.model_validate(
                _read_yaml(directory / "fare_classes.yaml")
            ),
            sources=[
                SourceDef.model_validate(s)
                for s in _as_list(_read_yaml(directory / "sources.yaml"), "sources")
            ],
        )
    except ValidationError as exc:
        raise ConfigurationError(f"invalid reference data: {exc}", path=str(directory)) from exc


def _as_list(document: object, key: str) -> list[object]:
    if not isinstance(document, dict) or not isinstance(document.get(key), list):
        raise ConfigurationError(f"reference document must contain a '{key}' list")
    return list(document[key])


@lru_cache(maxsize=1)
def get_reference_data() -> ReferenceData:
    return load_reference_data(get_settings().reference_dir)


def reset_reference_data() -> None:
    get_reference_data.cache_clear()
