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


class LinuxMountedComponentDiscoveryProvider:
    """Discover components across standard install roots and mounted data volumes.

    Mounts are re-read on every scan, so newly mounted SSDs/removable volumes
    become eligible without restarting the polling service. The filesystem root
    itself is not recursively searched; conventional Coreless install roots are
    included explicitly. Only manifest files are read.
    """

    _PSEUDO_FILESYSTEMS = frozenset({
        "proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "cgroup", "cgroup2",
        "overlay", "squashfs", "securityfs", "pstore", "debugfs", "tracefs",
        "configfs", "fusectl", "mqueue", "hugetlbfs", "rpc_pipefs",
    })

    def __init__(
        self,
        *,
        mount_table: str | Path = "/proc/self/mounts",
        install_roots: Iterable[str | Path] = (
            "/opt/coreless/components",
            "/var/lib/coreless/components",
        ),
        additional_roots: Iterable[str | Path] = (),
    ) -> None:
        self.mount_table = Path(mount_table)
        self.install_roots = tuple(Path(root) for root in install_roots)
        self.additional_roots = tuple(Path(root) for root in additional_roots)

    @staticmethod
    def _unescape_mount_field(value: str) -> str:
        # /proc/*/mounts uses three-digit octal escapes (e.g. \\040 for
        # space, \\011 for tab, \\012 for newline, \\134 for backslash).
        # Decode these in one pass so decoding \\134 cannot create a second
        # escape that gets decoded accidentally.
        import re

        return re.sub(
            r"\\\\([0-7]{3})",
            lambda match: chr(int(match.group(1), 8)),
            value,
        )

    def _mounted_roots(self) -> tuple[Path, ...]:
        roots: set[Path] = set()
        for root in (*self.install_roots, *self.additional_roots):
            if root.exists() and root.is_dir() and not root.is_symlink():
                roots.add(root)
        try:
            lines = self.mount_table.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            fields = line.split()
            if len(fields) < 3:
                continue
            mountpoint = Path(self._unescape_mount_field(fields[1]))
            filesystem = fields[2]
            if filesystem in self._PSEUDO_FILESYSTEMS or str(mountpoint) == "/":
                continue
            # Avoid probing transient kernel namespaces. Real mounted data
            # volumes elsewhere (including a separately mounted SSD) are kept.
            if str(mountpoint) in {"/proc", "/sys", "/dev", "/run/lock"}:
                continue
            try:
                if mountpoint.is_dir() and not mountpoint.is_symlink():
                    roots.add(mountpoint)
            except OSError:
                continue
        return tuple(sorted(roots, key=str))

    def enumerate_candidates(self) -> tuple[PortableComponentCandidate, ...]:
        roots = self._mounted_roots()
        if not roots:
            return ()
        return DirectoryComponentDiscoveryProvider(roots).enumerate_candidates()


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
        device_bridge: object | None = None,
    ) -> None:
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError("discovery interval must be positive")
        self.hub = hub
        self.provider = provider
        self.interval = float(interval)
        self.attach_options = dict(attach_options or {})
        self.on_error = on_error
        self.device_bridge = device_bridge
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def scan_once(self):
        discover = getattr(self.hub, "discover_and_attach", None)
        if not callable(discover):
            raise TypeError("Coreless Hub must expose discover_and_attach()")
        attached = discover(self.provider, **self.attach_options)
        if self.device_bridge is not None:
            reconcile = getattr(self.device_bridge, "reconcile", None)
            components = getattr(self.hub, "components", None)
            if not callable(reconcile) or not callable(components):
                raise TypeError("device bridge requires reconcile() and Hub components()")
            reconcile(components())
        return attached

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
