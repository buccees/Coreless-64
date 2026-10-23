"""Glue Linux udev lifecycle events into the Coreless hot-plug controller.

This is an integration boundary, not a USB/SATA/NVMe transport or identity
probe. A platform-specific resolver must correlate an observed OS device with
a freshly discoverable Coreless endpoint; HostHotplugController then performs
the adapter's fresh-snapshot and Coreless identity checks before attachment.
"""
from __future__ import annotations

from threading import RLock
from typing import Callable, Mapping

from host_transport import HostHotplugController
from linux_udev_events import LinuxDeviceEvent, LinuxUdevEventSource


class LinuxHostHotplugAdapter:
    """Drive validated Coreless attach/detach from native Linux udev events.

    `endpoint_id_for_event` must return an endpoint ID only when the platform
    transport/discovery layer can correlate the OS event with that endpoint.
    It must not treat USB serial/vendor/product identifiers alone as proof of
    Coreless identity. The controller re-enumerates and validates the endpoint
    before attaching it.

    `interface_factory` creates a CorelessHostInterface for a newly observed
    endpoint. Optional `attach_options` may return the keyword arguments
    accepted by HostHotplugController.device_arrived (system, host_io,
    input_router). All external callbacks are invoked outside the adapter lock.
    """

    def __init__(
        self,
        controller: HostHotplugController,
        interface_factory: Callable[[str], object],
        endpoint_id_for_event: Callable[[LinuxDeviceEvent], str | None],
        *,
        event_source: LinuxUdevEventSource | None = None,
        attach_options: Callable[[str, LinuxDeviceEvent], Mapping[str, object]] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if not isinstance(controller, HostHotplugController):
            raise TypeError("controller must be a HostHotplugController")
        if not callable(interface_factory):
            raise TypeError("interface_factory must be callable")
        if not callable(endpoint_id_for_event):
            raise TypeError("endpoint_id_for_event must be callable")
        if attach_options is not None and not callable(attach_options):
            raise TypeError("attach_options must be callable")
        if on_error is not None and not callable(on_error):
            raise TypeError("on_error must be callable")
        self._controller = controller
        self._interface_factory = interface_factory
        self._endpoint_id_for_event = endpoint_id_for_event
        self._attach_options = attach_options or (lambda endpoint_id, event: {})
        self._on_error = on_error or (lambda error: None)
        self._lock = RLock()
        self._syspath_to_endpoint: dict[str, str] = {}
        self._event_source = event_source or LinuxUdevEventSource(
            self.handle_event, on_error=self._report_error
        )

    @property
    def running(self) -> bool:
        return self._event_source.running

    @property
    def observed_endpoints(self) -> tuple[tuple[str, str], ...]:
        """Return a stable, sorted snapshot of tracked syspath/endpoint pairs."""
        with self._lock:
            return tuple(sorted(self._syspath_to_endpoint.items()))

    def start(self) -> bool:
        """Start native event monitoring."""
        return self._event_source.start()

    def stop(self) -> bool:
        """Stop native monitoring without detaching still-present devices."""
        return self._event_source.stop()

    def handle_event(self, event: LinuxDeviceEvent) -> None:
        """Consume one immutable udev snapshot; callback failures are reported."""
        try:
            if not isinstance(event, LinuxDeviceEvent):
                raise TypeError("event must be a LinuxDeviceEvent")
            if event.action in {"remove", "unbind"}:
                self._remove_event(event)
            elif event.action in {"add", "bind"}:
                self._arrive_event(event)
            elif event.action in {"change", "move"}:
                # Reconciliation is a recovery sweep, not an event source.
                # It safely drops stale attachments but never invents arrivals.
                self._controller.reconcile()
        except Exception as exc:
            self._report_error(exc)

    def _arrive_event(self, event: LinuxDeviceEvent) -> None:
        endpoint_id = self._endpoint_id_for_event(event)
        if endpoint_id is None:
            return
        if not isinstance(endpoint_id, str) or not endpoint_id.strip():
            raise ValueError("event resolver returned an invalid endpoint ID")

        # A sysfs path can be reused after a device is replaced. If the new
        # event resolves to a different Coreless endpoint, retire the previous
        # attachment before opening the replacement; otherwise the old endpoint
        # would remain attached after the syspath mapping is overwritten.
        with self._lock:
            previous_endpoint_id = self._syspath_to_endpoint.get(event.syspath)
        if previous_endpoint_id is not None and previous_endpoint_id != endpoint_id:
            self._controller.device_removed(previous_endpoint_id)
            with self._lock:
                if self._syspath_to_endpoint.get(event.syspath) == previous_endpoint_id:
                    self._syspath_to_endpoint.pop(event.syspath, None)

        interface = self._interface_factory(endpoint_id)
        options = self._attach_options(endpoint_id, event)
        if not isinstance(options, Mapping):
            raise TypeError("attach_options must return a mapping")
        allowed = {"system", "host_io", "input_router"}
        if any(key not in allowed for key in options):
            raise ValueError("attach_options contains unsupported arguments")
        # The controller obtains a fresh endpoint snapshot and the provider
        # adapter validates its identity before the interface is attached.
        self._controller.device_arrived(endpoint_id, interface, **dict(options))
        with self._lock:
            self._syspath_to_endpoint[event.syspath] = endpoint_id

    def _remove_event(self, event: LinuxDeviceEvent) -> None:
        with self._lock:
            endpoint_id = self._syspath_to_endpoint.pop(event.syspath, None)
        if endpoint_id is not None:
            self._controller.device_removed(endpoint_id)
        else:
            # A missed add event must not prevent stale-session cleanup.
            self._controller.reconcile()

    def _report_error(self, error: Exception) -> None:
        try:
            self._on_error(error)
        except Exception:
            # Error reporting must never terminate the udev observer thread.
            pass
