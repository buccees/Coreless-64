from reference.input import CoordinateFrame, InputEvent, InputEventType
from vigil.gesture import GestureInterpreter


def event(seq, kind, cid, x, y):
    return InputEvent(1, kind, "touch-1", seq, seq, CoordinateFrame.CORELESS, x=x, y=y, contact_id=cid)


def test_tap_and_swipe_are_deterministic():
    g = GestureInterpreter(movement_threshold=10)
    g.process(event(1, InputEventType.TOUCH_BEGIN, 1, 0, 0))
    tap = g.process(event(2, InputEventType.TOUCH_END, 1, 2, 2))
    assert tap[0].gesture == "tap"
    g.process(event(3, InputEventType.TOUCH_BEGIN, 1, 0, 0))
    swipe = g.process(event(4, InputEventType.TOUCH_END, 1, 20, 0))
    assert swipe[0].gesture == "swipe"
    assert swipe[0].metadata["direction"] == "right"


def test_multitouch_state_is_preserved():
    g = GestureInterpreter()
    g.process(event(1, InputEventType.TOUCH_BEGIN, 1, 0, 0))
    g.process(event(2, InputEventType.TOUCH_BEGIN, 2, 10, 0))
    result = g.process(event(3, InputEventType.TOUCH_UPDATE, 2, 20, 0))
    assert result[0].gesture == "multitouch_update"
    assert result[0].contacts == (1, 2)

from reference.input import InputCapabilities, PointingDevice
from vigil.input import VigilInputLayer


def test_gesture_results_are_routed_as_derived_input_events():
    layer = VigilInputLayer(enabled=True)
    device = PointingDevice(
        "touch-1", "touch", InputCapabilities(touch=True, multitouch=True)
    )
    layer.interpret(event(10, InputEventType.TOUCH_BEGIN, 1, 0, 0), device)
    derived = layer.interpret(event(11, InputEventType.TOUCH_END, 1, 1, 1), device)
    assert any(item.kind == "gesture.tap" for item in derived)
    assert all(item.device_id == "touch-1" for item in derived)
    assert all(item.source_sequence for item in derived)

def test_double_tap_and_long_press():
    g = GestureInterpreter(tap_window_ns=500, long_press_ns=600)
    g.process(event(20, InputEventType.TOUCH_BEGIN, 1, 5, 5))
    first = g.process(InputEvent(1, InputEventType.TOUCH_END, "touch-1", 20, 21, CoordinateFrame.CORELESS, x=5, y=5, contact_id=1))
    assert first[0].gesture == "tap"
    g.process(event(22, InputEventType.TOUCH_BEGIN, 1, 5, 5))
    second = g.process(InputEvent(1, InputEventType.TOUCH_END, "touch-1", 22 + 100_000_000, 122_000_000, CoordinateFrame.CORELESS, x=5, y=5, contact_id=1))
    assert second[0].gesture == "double_tap"
    g.process(event(30, InputEventType.TOUCH_BEGIN, 1, 0, 0))
    hold = g.process(InputEvent(1, InputEventType.TOUCH_END, "touch-1", 30 + 700_000_000, 700_000_001, CoordinateFrame.CORELESS, x=0, y=0, contact_id=1))
    assert hold[0].gesture == "long_press"


def test_pinch_and_rotate():
    g = GestureInterpreter(movement_threshold=5)
    g.process(event(1, InputEventType.TOUCH_BEGIN, 1, 0, 0))
    g.process(event(2, InputEventType.TOUCH_BEGIN, 2, 10, 0))
    pinch = g.process(event(3, InputEventType.TOUCH_UPDATE, 2, 20, 0))
    assert pinch[0].gesture == "pinch_out"
    g.process(event(4, InputEventType.TOUCH_END, 1, 0, 0))
