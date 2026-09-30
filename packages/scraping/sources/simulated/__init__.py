"""Synthetic market source (decision D8). Every quote it yields is flagged synthetic."""

from packages.scraping.sources.simulated.adapter import (
    SimulatedAirlineAdapter,
    SimulatedOtaAdapter,
)

__all__ = ["SimulatedAirlineAdapter", "SimulatedOtaAdapter"]
