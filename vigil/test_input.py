from reference.input import (
    CoordinateFrame,
    InputCapabilities,
    InputEvent,
    InputEventType,
    PointingDevice,
)
from vigil.input import VigilInputLayer
from vigil.spatial import CameraFrame


def test_vigil_is_optional_and_disabled_by_default():
    vigil = VigilInputLayer()
    assert not vigil.available()


def test_vigil_interprets_coreless_input_without_changing_raw_event():
    vigil = VigilInputLayer(enabled=True)
    device = PointingDevice(
        device_id="mouse-1",
        name="Mouse",
        capabilities=InputCapabilities(pointer=True, relative=True, buttons=2),
    )
    event = InputEvent(
        abi_version=1,
        event_type=InputEventType.POINTER_MOVE,
        device_id="mouse-1",
        timestamp_ns=10,
        sequence=1,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=10.0,
        y=20.0,
    )
    derived = vigil.interpret(event, device)
    assert len(derived) == 1
    assert derived[0].source_sequence == (1,)
    assert derived[0].kind == "input.pointer_move"


def test_camera_is_optional_and_deterministic():
    vigil = VigilInputLayer(enabled=True)
    frame = CameraFrame(
        source_id="camera-1",
        timestamp_ns=100,
        sequence=1,
        width=640,
        height=480,
    )
    vigil.ingest_camera_frame(frame)
    assert vigil.camera_frames == (frame,)


def test_disabled_vigil_does_not_accept_camera_work():
    vigil = VigilInputLayer()
    frame = CameraFrame("camera-1", 1, 1, 320, 240)
    try:
        vigil.ingest_camera_frame(frame)
    except RuntimeError:
        pass
    else:
        raise AssertionError("disabled VIGIL accepted camera input")


def test_runtime_input_uses_coreless_router_authority():
    from reference.input import CorelessInputRouter, InputCapabilities, InputEvent, InputEventType, CoordinateFrame, PointingDevice
    from vigil.runtime import VigilEnvironment

    router = CorelessInputRouter()
    router.devices.discover([PointingDevice("mouse", "mouse", InputCapabilities(pointer=True, relative=True, buttons=1))])
    router.devices.designate("mouse")
    environment = VigilEnvironment(enabled=True, input_router=router)
    event = InputEvent(
        1, InputEventType.POINTER_MOVE, "mouse", 10, 1, CoordinateFrame.CORELESS, x=4.0, y=5.0
    )
    derived = environment.ingest_input_event(event)
    assert len(router.raw_events) == 1
    assert len(derived) >= 1
    assert derived[0].device_id == "mouse"



def test_environment_enable_disable_keeps_coreless_router_in_sync():
    from reference.input import CorelessInputRouter, InputCapabilities, PointingDevice
    from vigil.runtime import VigilEnvironment

    router = CorelessInputRouter()
    router.devices.discover([
        PointingDevice("mouse", "mouse", InputCapabilities(pointer=True, relative=True, buttons=1))
    ])
    router.devices.designate("mouse")
    environment = VigilEnvironment(enabled=False, input_router=router)

    assert not router.vigil_enabled
    environment.enable()
    assert router.vigil is environment.input
    assert router.vigil_enabled

    environment.disable()
    assert not router.vigil_enabled

    environment.enable()
    assert router.vigil_enabled



def test_vigil_replay_contains_raw_and_derived_input_chain():
    from reference.input import CorelessInputRouter, InputEvent, InputEventType, CoordinateFrame, InputCapabilities, PointingDevice
    from vigil.runtime import VigilEnvironment

    router = CorelessInputRouter()
    router.devices.discover([
        PointingDevice("touch", "touch", InputCapabilities(touch=True, multitouch=True))
    ])
    router.devices.designate("touch")
    environment = VigilEnvironment(enabled=True, input_router=router)

    begin = InputEvent(1, InputEventType.TOUCH_BEGIN, "touch", 10, 1, CoordinateFrame.CORELESS, x=10, y=20, contact_id=1)
    end = InputEvent(1, InputEventType.TOUCH_END, "touch", 20, 2, CoordinateFrame.CORELESS, x=11, y=21, contact_id=1)
    environment.ingest_input_event(begin)
    environment.ingest_input_event(end)

    kinds = [event.kind for event in environment.replay_events()]
    assert kinds[:2] == ["input.raw", "input.raw"]
    assert "gesture.tap" in kinds
    assert environment.validate_persisted_replay_integrity().valid
