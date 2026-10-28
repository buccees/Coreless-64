"""Canonical server catalog for the six unique Pelagos historical artifacts.

Coordinates match the stable 42-by-42 world grid used by index.html. The server
ledger normalizes each cell center into the [0, 1] world coordinate space.
"""
from __future__ import annotations

ARTIFACT_CATALOG = (
    {"id": "PEL-ARCHIVE-EXPEDITION-HANDBOOK", "siteId": "PEL-PRIVATEERS-HOLD", "gridX": 5, "gridY": 7},
    {"id": "PEL-ARCHIVE-CHRONICLES", "siteId": "PEL-DAGGERFALL-01", "gridX": 21, "gridY": 21},
    {"id": "PEL-ARCHIVE-HISTORY-DAGGERFALL", "siteId": "PEL-CASTLE-DAGGERFALL", "gridX": 22, "gridY": 20},
    {"id": "PEL-ARCHIVE-COURT-LEDGER", "siteId": "PEL-CASTLE-WAYREST", "gridX": 14, "gridY": 8},
    {"id": "PEL-ARCHIVE-MACHINE-ANNOTATIONS", "siteId": "PEL-NUMIDIUM-SITE", "gridX": 3, "gridY": 24},
    {"id": "PEL-ARCHIVE-BURIAL-TESTIMONY", "siteId": "PEL-LYSANDUS-TOMB", "gridX": 18, "gridY": 15},
)


def build_artifact_catalog() -> list[dict[str, object]]:
    """Return fresh catalog rows with normalized stable cell-center coordinates."""
    return [
        {
            "id": item["id"],
            "siteId": item["siteId"],
            "x": (item["gridX"] + 0.5) / 42,
            "y": (item["gridY"] + 0.5) / 42,
        }
        for item in ARTIFACT_CATALOG
    ]
