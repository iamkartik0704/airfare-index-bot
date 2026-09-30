"""Source registry: ``sources.yaml`` id → adapter class.

Onboarding a source = write the adapter, add it to ``ADAPTERS``, add the
``sources.yaml`` entry and fixtures. Nothing downstream changes (doc 05).
"""

from __future__ import annotations

from packages.config.reference import ReferenceData, SourceDef
from packages.config.settings import Settings
from packages.domain.enums import SourceKind
from packages.domain.exceptions import ConfigurationError
from packages.scraping.sources.airlines.air_india import AirIndiaAdapter
from packages.scraping.sources.airlines.air_india_express import AirIndiaExpressAdapter
from packages.scraping.sources.airlines.akasa import AkasaAdapter
from packages.scraping.sources.airlines.indigo import IndigoAdapter
from packages.scraping.sources.airlines.spicejet import SpicejetAdapter
from packages.scraping.sources.base import BaseSourceAdapter
from packages.scraping.sources.otas.cleartrip import CleartripAdapter
from packages.scraping.sources.otas.easemytrip import EasemytripAdapter
from packages.scraping.sources.otas.ixigo import IxigoAdapter
from packages.scraping.sources.otas.makemytrip import MakemytripAdapter
from packages.scraping.sources.otas.yatra import YatraAdapter
from packages.scraping.sources.simulated import SimulatedAirlineAdapter, SimulatedOtaAdapter

ADAPTERS: dict[str, type[BaseSourceAdapter]] = {
    cls.source_id: cls
    for cls in (
        IndigoAdapter,
        AirIndiaAdapter,
        AirIndiaExpressAdapter,
        AkasaAdapter,
        SpicejetAdapter,
        MakemytripAdapter,
        YatraAdapter,
        EasemytripAdapter,
        CleartripAdapter,
        IxigoAdapter,
        SimulatedAirlineAdapter,
        SimulatedOtaAdapter,
    )
}


def build_adapter(definition: SourceDef) -> BaseSourceAdapter:
    try:
        adapter_cls = ADAPTERS[definition.id]
    except KeyError as exc:
        raise ConfigurationError("no adapter registered for source", source=definition.id) from exc
    return adapter_cls(definition)


def is_runnable(definition: SourceDef, settings: Settings) -> bool:
    """Whether the sweep generator should schedule this source at all."""
    if definition.id not in ADAPTERS or not definition.enabled:
        return False
    if definition.kind is SourceKind.SIMULATED:
        return settings.simulated_source_enabled
    return definition.tos_reviewed


def runnable_sources(reference: ReferenceData, settings: Settings) -> list[SourceDef]:
    return [s for s in reference.sources if is_runnable(s, settings)]
