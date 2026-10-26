"""Unofficial Alien: Earth crossover scenario faction roster for VIGIL.

This optional scenario uses the five corporate factions named by FX's
Alien: Earth. It is fan-made scenario data, not an official franchise product.
The base VIGIL campaign can continue using its own original faction IDs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioFaction:
    faction_id: str
    display_name: str


ALIEN_EARTH_CORPORATIONS = (
    ScenarioFaction("prodigy", "Prodigy"),
    ScenarioFaction("weyland-yutani", "Weyland-Yutani"),
    ScenarioFaction("lynch", "Lynch"),
    ScenarioFaction("dynamic", "Dynamic"),
    ScenarioFaction("threshold", "Threshold"),
)

SCENARIO_ID = "alien-earth-corporate-rivalries"
SCENARIO_TITLE = "Corporate Rivalries"
SCENARIO_NOTICE = (
    "Unofficial fan-made crossover scenario inspired by FX's Alien: Earth; "
    "not affiliated with or endorsed by the rights holders."
)


def faction_ids() -> tuple[str, ...]:
    """Return canonical faction IDs in stable scenario order."""
    return tuple(faction.faction_id for faction in ALIEN_EARTH_CORPORATIONS)


def faction_by_id(faction_id: str) -> ScenarioFaction:
    """Resolve a scenario faction ID without accepting unknown affiliations."""
    for faction in ALIEN_EARTH_CORPORATIONS:
        if faction.faction_id == faction_id:
            return faction
    raise ValueError(f"unknown Alien: Earth scenario faction: {faction_id}")
