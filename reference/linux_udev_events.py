"""Optional Linux udev event source for the Coreless host boundary.

This module observes OS device lifecycle events only. It does not identify a
Coreless endpoint, open a transport, or claim that hot-plug is end-to-end ready.
A platform integration must validate the event and resolve the device through
the Coreless identity/discovery protocol before touching HostHotplugController.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Mapping

SAFE_PROPERTIES = (
    "SUBSYSTEM", "DEVTYPE", "DEVNAME", "ID_BUS", "ID_PATH",
    "ID_VENDOR_ID", "ID_MODEL_ID", "ID_SERIAL",
)


@dataclass(frozen=True)
class LinuxDeviceEvent:
    """Small immutable snapshot of one kernel device event."""

    action: str
    syspath: str
    subsystem: str | None
    devtype: str | None
    sys_name: str
    properties: tuple[tuple[str, str], ...]

    def property_map(self) -> dict[str, str]:
        """Return a copy of the allowlisted udev properties."""
        return dict(self.properties)


def snapshot_udev_event(action: object, device: object) -> LinuxDeviceEvent:
    """Copy only stable, allowlisted fields from a pyudev-like device object."""
    if not isinstance(action, str) or not action.strip():
        raise ValueError("udev action must be non-empty text")
    syspath = getattr(device, "sys_path", None)
    if not isinstance(syspath, str) or not syspath.strip():
        raise ValueError("udev device must expose a non-empty sys_path")

    raw_properties = getattr(device, "properties", {})
    if not isinstance(raw_properties, Mapping):
        try:
            raw_properties = dict(raw_properties)
        except (TypeError, ValueError):
            raw_properties = {}

    properties = []
    for key in SAFE_PROPERTIES:
        value = raw_properties.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            properties.append((key, str(value)))

    subsystem = getattr(device, "subsystem", None)
    devtype = getattr(device, "device_type", None)
    sys_name = getattr(device, "sys_name", "")
    return LinuxDeviceEvent(
        action=action.strip().lower(),
        syspath=syspath,
        subsystem=subsystem if isinstance(subsystem, str) else None,
        devtype=devtype if isinstance(devtype, str) else None,
        sys_name=sys_name if isinstance(sys_name, str) else "",
        properties=tuple(properties),
    )


class LinuxUdevEventSource:
    """Lifecycle-safe optional pyudev observer with injectable test factories.

    pyudev is imported lazily, so other platforms and test environments do not
    need the optional package installed merely to import this module. Callbacks
    receive immutable snapshots, never raw mutable device objects. The caller
    remains responsible for Coreless identity verification and transport I/O.
    """

    def __init__(
        self,
        on_event: Callable[[LinuxDeviceEvent], None],
        *,
        on_error: Callable[[Exception], None] | None = None,
        monitor_factory: Callable[[], object] | None = None,
        observer_factory: Callable[[object, Callable[..., None]], object] | None = None,
    ) -> None:
        if not callable(on_event):
            raise TypeError("on_event must be callable")
        if on_error is not None and not callable(on_error):
            raise TypeError("on_error must be callable")
        self._on_event = on_event
        self._on_error = on_error or (lambda error: None)
        self._monitor_factory = monitor_factory
        self._observer_factory = observer_factory
        self._observer = None
        self._lock = RLock()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._observer is not None

    def start(self) -> bool:
        """Start observing kernel device events; False means already running."""
        with self._lock:
            if self._observer is not None:
                return False

            monitor_factory = self._monitor_factory
            observer_factory = self._observer_factory
            if monitor_factory is None or observer_factory is None:
                try:
                    import pyudev
                except ImportError as exc:
                    raise RuntimeError(
                        "Linux udev monitoring requires the optional 'pyudev' package"
                    ) from exc
                monitor_factory = monitor_factory or (
                    lambda: pyudev.Monitor.from_netlink(pyudev.Context())
                )
                observer_factory = observer_factory or (
                    lambda monitor, callback: pyudev.MonitorObserver(
                        monitor, callback=callback, name="coreless-udev"
                    )
                )

            monitor = monitor_factory()
            observer = observer_factory(monitor, self._dispatch)
            try:
                observer.start()
            except Exception:
                stop = getattr(observer, "stop", None)
                if callable(stop):
                    try:
                        stop()
                    except Exception as cleanup_error:
                        self._report_error(cleanup_error)
                raise
            self._observer = observer
            return True

    def stop(self) -> bool:
        """Stop the observer; repeated calls are harmless."""
        with self._lock:
            observer = self._observer
            if observer is None:
                return False
            self._observer = None
        stop = getattr(observer, "stop", None)
        if callable(stop):
            stop()
        return True

    def _dispatch(self, action: object, device: object) -> None:
        try:
            self._on_event(snapshot_udev_event(action, device))
        except Exception as exc:
            self._report_error(exc)

    def _report_error(self, error: Exception) -> None:
        try:
            self._on_error(error)
        except Exception:
            # Error reporting must not terminate the kernel observer thread.
            pass
