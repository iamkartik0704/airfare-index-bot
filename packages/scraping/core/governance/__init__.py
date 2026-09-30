"""Ethical-scraping governance: robots.txt and block detection (doc 15)."""

from packages.scraping.core.governance.blocking import detect_block, raise_for_response
from packages.scraping.core.governance.robots import RobotsDecision, RobotsGate, RobotsPolicy

__all__ = ["RobotsDecision", "RobotsGate", "RobotsPolicy", "detect_block", "raise_for_response"]
