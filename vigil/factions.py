"""Canonical factions available to the VIGIL simulation.

Corporate faction names are included directly in the game's shared faction
catalog. Scenario designers can assign ships with these IDs or add custom
factions in configuration; the catalog itself does not imply diplomacy rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Faction:
    faction_id: str
    name: str
    category: str


FACTIONS = (
    Faction("maritime-coalition", "Maritime Coalition", "state"),
    Faction("extraction-directorate", "Extraction Directorate", "corporate"),
    Faction("unknown", "Unknown", "nonhuman"),
    Faction("prodigy", "Prodigy", "corporate"),
    Faction("weyland-yutani", "Weyland-Yutani", "corporate"),
    Faction("lynch", "Lynch", "corporate"),
    Faction("dynamic", "Dynamic", "corporate"),
    Faction("threshold", "Threshold", "corporate"),
)

FACTIONS_BY_ID = {faction.faction_id: faction for faction in FACTIONS}


def public_faction_catalog() -> list[dict[str, str]]:
    """Return stable, client-safe faction entries for the simulation snapshot."""
    return [asdict(faction) for faction in FACTIONS]
