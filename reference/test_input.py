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



def test_device_state_from_discovered_arduino_does_not_steal_pointer_focus():
    manager = PointingDeviceManager()
    mouse = device("mouse-1")
    arduino = PointingDevice(
        device_id="arduino-1",
        name="Arduino sensor board",
        capabilities=InputCapabilities(),
    )
    manager.discover([mouse, arduino])
    manager.designate("mouse-1")
    router = CorelessInputRouter(manager)

    state_event = InputEvent(
        abi_version=1,
        event_type=InputEventType.DEVICE_STATE,
        device_id="arduino-1",
        timestamp_ns=100,
        sequence=0,
        coordinate_frame=CoordinateFrame.HOST,
        metadata={"source": "arduino", "value": 512},
    )
    assert router.submit(state_event) == ()
    assert router.raw_events == (state_event,)
    assert manager.bound_device_id == "mouse-1"


def test_input_sequences_are_monotonic_per_device_not_globally():
    manager = PointingDeviceManager()
    manager.discover([device("mouse-1"), PointingDevice(
        device_id="arduino-1",
        name="Arduino sensor board",
        capabilities=InputCapabilities(),
    )])
    manager.designate("mouse-1")
    router = CorelessInputRouter(manager)
    sensor = InputEvent(
        abi_version=1,
        event_type=InputEventType.DEVICE_STATE,
        device_id="arduino-1",
        timestamp_ns=100,
        sequence=0,
        coordinate_frame=CoordinateFrame.HOST,
    )
    pointer = InputEvent(
        abi_version=1,
        event_type=InputEventType.TOUCH_BEGIN,
        device_id="mouse-1",
        timestamp_ns=101,
        sequence=1,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=1,
        y=2,
    )
    assert router.submit(sensor) == ()
    assert router.submit(pointer) == ()
    with __import__("pytest").raises(ValueError, match="monotonically"):
        router.submit(sensor)


def test_device_state_from_undiscovered_device_is_rejected():
    import pytest

    manager = PointingDeviceManager()
    manager.discover([device("mouse-1")])
    manager.designate("mouse-1")
    router = CorelessInputRouter(manager)
    sensor = InputEvent(
        abi_version=1,
        event_type=InputEventType.DEVICE_STATE,
        device_id="unknown-board",
        timestamp_ns=100,
        sequence=0,
        coordinate_frame=CoordinateFrame.HOST,
    )
    with pytest.raises(PermissionError, match="discovered"):
        router.submit(sensor)



def test_input_timestamps_must_not_move_backwards_per_device():
    import pytest

    manager = PointingDeviceManager()
    manager.discover([device()])
    manager.designate("touch-1")
    router = CorelessInputRouter(manager)

    assert router.submit(event(sequence=2)) == ()
    earlier_timestamp = InputEvent(
        abi_version=1,
        event_type=InputEventType.TOUCH_BEGIN,
        device_id="touch-1",
        timestamp_ns=1001,
        sequence=3,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=10.0,
        y=20.0,
        contact_id=1,
    )
    with pytest.raises(ValueError, match="timestamp must not move backwards"):
        router.submit(earlier_timestamp)

    assert len(router.raw_events) == 1
    assert router.raw_events[0].sequence == 2



def test_input_event_rejects_malformed_direct_construction():
    import pytest

    base = dict(
        abi_version=1,
        event_type=InputEventType.POINTER_MOVE,
        device_id="mouse-1",
        timestamp_ns=1,
        sequence=1,
        coordinate_frame=CoordinateFrame.HOST,
        x=1.0,
        y=2.0,
    )
    with pytest.raises(ValueError, match="timestamp_ns must be an integer"):
        InputEvent(**{**base, "timestamp_ns": True})
    with pytest.raises(ValueError, match="sequence must be an integer"):
        InputEvent(**{**base, "sequence": True})
    with pytest.raises(ValueError, match="coordinates must be finite"):
        InputEvent(**{**base, "x": float("nan")})
    with pytest.raises(ValueError, match="event_type must be"):
        InputEvent(**{**base, "event_type": "pointer_move"})
    with pytest.raises(ValueError, match="pressure must be a finite"):
        InputEvent(**{**base, "pressure": float("inf")})



def test_input_event_metadata_is_a_defensive_read_only_snapshot():
    import pytest

    original = {"source": "host", "sequence_hint": 7}
    raw = InputEvent(
        abi_version=1,
        event_type=InputEventType.POINTER_MOVE,
        device_id="mouse-1",
        timestamp_ns=10,
        sequence=1,
        coordinate_frame=CoordinateFrame.HOST,
        x=1.0,
        y=2.0,
        metadata=original,
    )
    original["source"] = "mutated"
    original["extra"] = True

    assert raw.metadata["source"] == "host"
    assert "extra" not in raw.metadata
    with pytest.raises(TypeError):
        raw.metadata["source"] = "tampered"


def test_interpreted_input_metadata_is_a_defensive_read_only_snapshot():
    import pytest
    from input import InterpretedInputEvent

    original = {"source_sequence": 4}
    derived = InterpretedInputEvent(
        interpretation_id="interpretation-1",
        kind="tap",
        device_id="touch-1",
        timestamp_ns=10,
        source_sequence=(4,),
        metadata=original,
        confidence=0.8,
    )
    original["source_sequence"] = 99

    assert derived.metadata["source_sequence"] == 4
    with pytest.raises(TypeError):
        derived.metadata["source_sequence"] = 99

def test_raw_input_survives_vigil_adapter_exceptions():
    class BrokenAvailability(FakeVigil):
        def available(self):
            raise RuntimeError("VIGIL transport unavailable")

    class BrokenInterpreter(FakeVigil):
        def interpret(self, event, device):
            raise RuntimeError("VIGIL interpreter crashed")

    import pytest

    for broken in (BrokenAvailability(), BrokenInterpreter()):
        manager = PointingDeviceManager()
        manager.discover([device()])
        manager.designate("touch-1")
        router = CorelessInputRouter(manager, broken)

        assert router.submit(event()) == ()
        assert len(router.raw_events) == 1
        assert router.vigil_enabled is False
        # Once the optional adapter faults, normal raw input continues without
        # repeatedly invoking the broken integration.
        assert router.submit(event(sequence=2)) == ()
        assert len(router.raw_events) == 2




def test_malformed_vigil_derived_output_falls_back_to_raw_input():
    from input import InterpretedInputEvent

    class NullOutput(FakeVigil):
        def interpret(self, event, device):
            return None

    class WrongProvenance(FakeVigil):
        def interpret(self, event, device):
            return (InterpretedInputEvent(
                interpretation_id="wrong-source",
                kind="gesture.tap",
                device_id=device.device_id,
                timestamp_ns=event.timestamp_ns,
                source_sequence=(event.sequence + 1,),
            ),)

    import pytest

    for broken in (NullOutput(), WrongProvenance()):
        manager = PointingDeviceManager()
        manager.discover([device()])
        manager.designate("touch-1")
        router = CorelessInputRouter(manager, broken)

        assert router.submit(event()) == ()
        assert len(router.raw_events) == 1
        assert router.interpreted_events == ()
        assert router.vigil_enabled is False
        assert router.submit(event(sequence=2)) == ()
        assert len(router.raw_events) == 2
