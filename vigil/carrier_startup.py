"""Startup wiring for VIGIL's persistent spatial state on the Coreless carrier."""
from __future__ import annotations

from pathlib import Path

from .spatial_registry_store import SpatialRegistryStore
from .workspace import SpatialWorkspace


def open_carrier_spatial_workspace(database_path: str | Path) -> tuple[SpatialRegistryStore, SpatialWorkspace]:
    """Open the carrier-owned VIGIL database and restore its workspace.

    The caller owns the returned store and must close it during shutdown. Keeping
    this path separate from the Coreless machine image makes VIGIL's registry
    durable across machine-image upgrades and carrier reboots.
    """
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    store = SpatialRegistryStore(str(path))
    try:
        workspace = SpatialWorkspace(registry_store=store)
    except Exception:
        store.close()
        raise
    return store, workspace
