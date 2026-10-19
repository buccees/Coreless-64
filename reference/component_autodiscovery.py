"""Automatic discovery of portable Coreless software peripherals on mounted media.

The provider scans configured mount roots for declarative component manifests.
It does not execute files from removable media. OS-level mount/device discovery
can feed mount roots to this provider; a poller repeatedly notices new manifests.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class PortableComponentCandidate:
    endpoint_id: str
    manifest: bytes


class DirectoryComponentDiscoveryProvider:
    """Discover manifests from mounted component directories and manifest files.

    Recognized layouts:
      * <mount-root>/*.coreless.json
      * <mount-root>/<package>/component.coreless.json
      * <mount-root>/<package>/component.json

    The provider reads only manifest metadata. It never imports or executes
    component code from removable storage.
    """

    def __init__(self, mount_roots: Iterable[str | Path]) -> None:
        self._roots = tuple(Path(root) for root in mount_roots)
        if not self._roots:
            raise ValueError("at least one component mount root is required")

    def enumerate_candidates(self) -> tuple[PortableComponentCandidate, ...]:
        found: dict[str, PortableComponentCandidate] = {}
        for root in self._roots:
            if not root.exists() or not root.is_dir() or root.is_symlink():
                continue
            paths: list[Path] = []
            try:
                for item in root.iterdir():
                    if item.is_symlink():
                        continue
                    if item.is_file() and item.name.endswith(".coreless.json"):
                        paths.append(item)
                    elif item.is_dir():
                        for name in ("component.coreless.json", "component.json"):
                            candidate = item / name
                            if candidate.is_file() and not candidate.is_symlink():
                                paths.append(candidate)
            except OSError:
                # A removable drive can disappear during enumeration. Its
                # next poll can retry; no partial path is treated as attached.
                continue
            for path in sorted(paths, key=lambda value: str(value)):
                try:
                    raw = path.read_bytes()
                    payload = json.loads(raw.decode("utf-8"))
                    descriptor = payload.get("descriptor") if isinstance(payload, dict) else None
                    component_id = descriptor.get("component_id") if isinstance(descriptor, dict) else None
                    if not isinstance(component_id, str) or not component_id:
                        continue
                    endpoint_id = str(path.resolve())
                    candidate = PortableComponentCandidate(endpoint_id, raw)
                    previous = found.get(component_id)
                    if previous is not None and previous.manifest != raw:
                        raise ValueError(
                            f"conflicting portable manifests advertise component {component_id!r}"
                        )
                    found[component_id] = candidate
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    # An incomplete copy is ignored until a later poll sees a
                    # complete, valid manifest.
                    continue
        return tuple(found[key] for key in sorted(found))


class ComponentAutoDiscoveryService:
    """Poll a discovery provider and auto-attach newly available peripherals."""

    def __init__(
        self,
        hub: object,
        provider: object,
        *,
        interval: float = 1.0,
        attach_options: Mapping[str, object] | None = None,
        on_error=None,
    ) -> None:
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError("discovery interval must be positive")
        self.hub = hub
        self.provider = provider
        self.interval = float(interval)
        self.attach_options = dict(attach_options or {})
        self.on_error = on_error
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def scan_once(self):
        discover = getattr(self.hub, "discover_and_attach", None)
        if not callable(discover):
            raise TypeError("Coreless Hub must expose discover_and_attach()")
        return discover(self.provider, **self.attach_options)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="coreless-component-discovery", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float | None = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError("component auto-discovery service did not stop in time")
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception as exc:
                if self.on_error is not None:
                    self.on_error(exc)
            self._stop.wait(self.interval)
