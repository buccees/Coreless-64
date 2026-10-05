from vigil.visual_pointer import VisualTouchIntent

from .input import CorelessInputRouter, InputEventType
from .visual_input import VisualPointingDeviceAdapter


def test_visual_touch_intents_reach_coreless_input_boundary():
    router = CorelessInputRouter()
    adapter = VisualPointingDeviceAdapter(router)
    adapter.register_and_designate()

    begin = adapter.submit(VisualTouchIntent(
        "touch_begin", 100.0, 200.0, 10, "d1", 0.95, "camera-1"
    ))
    move = adapter.submit(VisualTouchIntent(
        "move", 110.0, 205.0, 11, "d2", 0.92, "camera-1"
    ))
    end = adapter.submit(VisualTouchIntent(
        "touch_end", 110.0, 205.0, 12, "d3", 0.91, "camera-1"
    ))

    assert [event.event_type for event in router.raw_events] == [
        InputEventType.TOUCH_BEGIN,
        InputEventType.TOUCH_UPDATE,
        InputEventType.TOUCH_END,
    ]
    assert [event.sequence for event in router.raw_events] == [0, 1, 2]
    assert begin.metadata["source"] == "vigil-visual-pointer"
    assert move.x == 110.0
    assert end.contact_id == 0


def test_visual_device_is_explicitly_designated():
    router = CorelessInputRouter()
    adapter = VisualPointingDeviceAdapter(router)
    device = adapter.register_and_designate()

    assert router.devices.designated_device_id == device.device_id
    assert router.devices.bound_device_id == device.device_id
    assert device.capabilities.touch
    assert device.capabilities.absolute
