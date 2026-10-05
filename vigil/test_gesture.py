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
