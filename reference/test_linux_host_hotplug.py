import sys
sys.path.insert(0, ".")

from dataclasses import dataclass

import pytest

from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint, HostHotplugController, MemoryHostTransportAdapter
from linux_host_hotplug import LinuxHostHotplugAdapter
from linux_udev_events import LinuxDeviceEvent


def endpoint(endpoint_id="coreless-1", computer_id="machine-1"):
    return HostEndpoint(
        endpoint_id=endpoint_id,
        identity=CorelessIdentity(computer_id),
        capabilities=HostCapabilities(display=True, input=True),
        channels={},
    )


def event(action, syspath="/sys/devices/test/1-1", serial="CORELESS-1"):
    return LinuxDeviceEvent(
        action=action,
        syspath=syspath,
        subsystem="usb",
        devtype="usb_device",
        sys_name="1-1",
        properties=(("SUBSYSTEM", "usb"), ("ID_SERIAL", serial)),
    )


class FakeEventSource:
    def __init__(self, callback):
        self.callback = callback
        self.running = False

    def start(self):
        if self.running:
            return False
        self.running = True
        return True

    def stop(self):
        if not self.running:
            return False
        self.running = False
        return True

    def emit(self, item):
        self.callback(item)


def make_adapter():
    endpoint_record = endpoint()
    transport = MemoryHostTransportAdapter([endpoint_record])
    controller = HostHotplugController(transport)
    errors = []
    source = FakeEventSource(lambda item: None)
    adapter = LinuxHostHotplugAdapter(
        controller,
        lambda endpoint_id: CorelessHostInterface(CorelessIdentity("machine-1")),
        lambda item: "coreless-1" if item.property_map().get("ID_SERIAL") == "CORELESS-1" else None,
        event_source=source,
        on_error=errors.append,
    )
    source.callback = adapter.handle_event
    return adapter, controller, transport, source, errors


def test_linux_hotplug_adapter_starts_and_stops_native_source_idempotently():
    adapter, _, _, source, _ = make_adapter()
    assert adapter.running is False
    assert adapter.start() is True
    assert adapter.start() is False
    assert adapter.running is True
    assert adapter.stop() is True
    assert adapter.stop() is False
    assert adapter.running is False


def test_add_event_attaches_only_after_controller_fresh_discovery():
    adapter, controller, _, source, errors = make_adapter()
    source.emit(event("add"))

    assert controller.attached_endpoint_ids == ("coreless-1",)
    assert adapter.observed_endpoints == (("/sys/devices/test/1-1", "coreless-1"),)
    assert errors == []


def test_remove_event_detaches_and_duplicate_remove_is_safe():
    adapter, controller, transport, source, errors = make_adapter()
    source.emit(event("add"))
    assert controller.attached_endpoint_ids == ("coreless-1",)

    transport.unregister("coreless-1")
    source.emit(event("remove"))
    source.emit(event("remove"))

    assert controller.attached_endpoint_ids == ()
    assert adapter.observed_endpoints == ()
    assert errors == []


def test_unrecognized_device_does_not_attach_coreless():
    adapter, controller, _, source, errors = make_adapter()
    source.emit(event("add", serial="ordinary-usb-drive"))

    assert controller.attached_endpoint_ids == ()
    assert adapter.observed_endpoints == ()
    assert errors == []


def test_add_event_for_endpoint_absent_from_fresh_snapshot_is_reported():
    adapter, controller, transport, source, errors = make_adapter()
    transport.unregister("coreless-1")
    source.emit(event("add"))

    assert controller.attached_endpoint_ids == ()
    assert len(errors) == 1
    assert "not present in current discovery snapshot" in str(errors[0])


def test_change_event_reconciles_stale_attachment_without_fabricating_arrival():
    adapter, controller, transport, source, errors = make_adapter()
    source.emit(event("add"))
    transport.unregister("coreless-1")

    source.emit(event("change"))

    assert controller.attached_endpoint_ids == ()
    assert errors == []


def test_attach_options_reject_unknown_arguments_without_attaching():
    record = endpoint()
    transport = MemoryHostTransportAdapter([record])
    controller = HostHotplugController(transport)
    errors = []
    source = FakeEventSource(lambda item: None)
    adapter = LinuxHostHotplugAdapter(
        controller,
        lambda endpoint_id: CorelessHostInterface(CorelessIdentity("machine-1")),
        lambda item: "coreless-1",
        event_source=source,
        attach_options=lambda endpoint_id, item: {"surprise": True},
        on_error=errors.append,
    )
    source.callback = adapter.handle_event
    source.emit(event("add"))

    assert controller.attached_endpoint_ids == ()
    assert len(errors) == 1
    assert "unsupported arguments" in str(errors[0])


def test_error_callback_failure_does_not_escape_event_handler():
    record = endpoint()
    transport = MemoryHostTransportAdapter([record])
    controller = HostHotplugController(transport)
    source = FakeEventSource(lambda item: None)
    adapter = LinuxHostHotplugAdapter(
        controller,
        lambda endpoint_id: CorelessHostInterface(CorelessIdentity("wrong-machine")),
        lambda item: "coreless-1",
        event_source=source,
        on_error=lambda exc: (_ for _ in ()).throw(RuntimeError("reporter failed")),
    )
    source.callback = adapter.handle_event

    adapter.handle_event(event("add"))

    assert controller.attached_endpoint_ids == ()
