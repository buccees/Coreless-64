import pytest

from linux_udev_events import LinuxUdevEventSource, snapshot_udev_event


class FakeDevice:
    sys_path = "/sys/devices/test/usb1/1-1"
    subsystem = "usb"
    device_type = "usb_device"
    sys_name = "1-1"
    properties = {
        "SUBSYSTEM": "usb",
        "DEVTYPE": "usb_device",
        "ID_BUS": "usb",
        "ID_SERIAL": "CORELESS-TEST-1",
        "SECRET_PROPERTY": "must-not-leak",
    }


class FakeObserver:
    def __init__(self, monitor, callback):
        self.monitor = monitor
        self.callback = callback
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_snapshot_udev_event_copies_only_allowlisted_properties():
    event = snapshot_udev_event("ADD", FakeDevice())
    assert event.action == "add"
    assert event.syspath == FakeDevice.sys_path
    assert event.subsystem == "usb"
    assert event.property_map() == {
        "SUBSYSTEM": "usb",
        "DEVTYPE": "usb_device",
        "ID_BUS": "usb",
        "ID_SERIAL": "CORELESS-TEST-1",
    }
    assert "SECRET_PROPERTY" not in event.property_map()


@pytest.mark.parametrize("action,device", [
    ("", FakeDevice()),
    (None, FakeDevice()),
    ("remove", object()),
])
def test_snapshot_udev_event_rejects_missing_identity_fields(action, device):
    with pytest.raises(ValueError):
        snapshot_udev_event(action, device)


def test_linux_udev_event_source_starts_once_dispatches_snapshot_and_stops():
    received = []
    observers = []

    def observer_factory(monitor, callback):
        observer = FakeObserver(monitor, callback)
        observers.append(observer)
        return observer

    source = LinuxUdevEventSource(
        received.append,
        monitor_factory=lambda: "fake-monitor",
        observer_factory=observer_factory,
    )
    assert source.running is False
    assert source.start() is True
    assert source.running is True
    assert source.start() is False
    assert observers[0].started is True

    observers[0].callback("add", FakeDevice())
    assert len(received) == 1
    assert received[0].action == "add"
    assert received[0].property_map()["ID_SERIAL"] == "CORELESS-TEST-1"

    assert source.stop() is True
    assert source.running is False
    assert observers[0].stopped is True
    assert source.stop() is False


def test_linux_udev_event_source_reports_callback_errors_without_raising():
    errors = []
    source = LinuxUdevEventSource(
        lambda event: (_ for _ in ()).throw(RuntimeError("consumer failed")),
        on_error=errors.append,
        monitor_factory=lambda: object(),
        observer_factory=lambda monitor, callback: FakeObserver(monitor, callback),
    )
    source.start()
    source._dispatch("add", FakeDevice())
    assert len(errors) == 1
    assert str(errors[0]) == "consumer failed"
    source.stop()


def test_linux_udev_event_source_cleans_up_if_observer_start_fails():
    observer = FakeObserver(None, None)

    def fail_start():
        def broken_start():
            raise RuntimeError("monitor unavailable")
        observer.start = broken_start
        return observer

    source = LinuxUdevEventSource(
        lambda event: None,
        monitor_factory=lambda: object(),
        observer_factory=lambda monitor, callback: fail_start(),
    )
    with pytest.raises(RuntimeError, match="monitor unavailable"):
        source.start()
    assert source.running is False
    assert observer.stopped is True
