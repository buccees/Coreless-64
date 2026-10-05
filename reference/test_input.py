from input import (
    CoordinateFrame,
    CorelessInputRouter,
    InputCapabilities,
    InputEvent,
    InputEventType,
    PointingDevice,
    PointingDeviceManager,
)


class FakeVigil:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def available(self):
        return self.enabled

    def interpret(self, event, device):
        return (
            __import__("input").InterpretedInputEvent(
                interpretation_id="tap-1",
                kind="gesture.tap",
                device_id=device.device_id,
                timestamp_ns=event.timestamp_ns,
                source_sequence=(event.sequence,),
                confidence=1.0,
            ),
        )


def device(device_id="touch-1"):
    return PointingDevice(
        device_id=device_id,
        name="Designated Touch Device",
        capabilities=InputCapabilities(
            pointer=True,
            absolute=True,
            touch=True,
            multitouch=True,
        ),
    )


def event(sequence=1):
    return InputEvent(
        abi_version=1,
        event_type=InputEventType.TOUCH_BEGIN,
        device_id="touch-1",
        timestamp_ns=1000 + sequence,
        sequence=sequence,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=10.0,
        y=20.0,
        contact_id=1,
    )


def test_designation_and_restore():
    manager = PointingDeviceManager()
    manager.discover([device()])
    manager.designate("touch-1")
    state = manager.persistent_state()

    restored = PointingDeviceManager()
    restored.discover([device()])
    restored.restore_state(state)

    assert restored.designated_device_id == "touch-1"
    assert restored.bound_device_id == "touch-1"


def test_raw_input_survives_without_vigil():
    manager = PointingDeviceManager()
    manager.discover([device()])
    manager.designate("touch-1")
    router = CorelessInputRouter(manager)
    assert router.submit(event()) == ()
    assert len(router.raw_events) == 1


def test_vigil_interpretation_is_derived():
    manager = PointingDeviceManager()
    manager.discover([device()])
    manager.designate("touch-1")
    router = CorelessInputRouter(manager, FakeVigil())
    result = router.submit(event())

    assert result[0].kind == "gesture.tap"
    assert router.raw_events[0].sequence == 1
    assert router.interpreted_events[0].source_sequence == (1,)


def test_vigil_unavailable_falls_back_to_raw():
    manager = PointingDeviceManager()
    manager.discover([device()])
    manager.designate("touch-1")
    router = CorelessInputRouter(manager, FakeVigil(enabled=False))
    assert router.submit(event()) == ()
    assert len(router.raw_events) == 1
