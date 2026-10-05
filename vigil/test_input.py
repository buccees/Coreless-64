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
