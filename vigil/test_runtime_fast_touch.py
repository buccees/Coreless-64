from vigil.runtime import VigilEnvironment
from vigil.model import Detection, EntityType, Provenance
from vigil.spatial import CameraFrame
from reference.input import CorelessInputRouter, InputEventType


class Camera:
    def __init__(self):
        self.sequence = 0

    def available(self):
        return True

    def read(self):
        self.sequence += 1
        return CameraFrame("camera-1", self.sequence * 1_000_000, self.sequence, 1920, 1080)


class Detector:
    def detect(self, frame):
        return Detection(
            detection_id=f"d{frame.sequence}",
            observation_id=f"o{frame.sequence}",
            entity_type=EntityType.PERSON,
            label="finger",
            timestamp_ns=frame.timestamp_ns,
            position=(100.0 + frame.sequence, 200.0, 0.0),
            confidence=0.95,
            uncertainty=None,
            provenance=(Provenance("camera-1", "camera", frame.timestamp_ns),),
        )


def test_runtime_submits_visual_touch_to_coreless_input():
    router = CorelessInputRouter()
    env = VigilEnvironment(enabled=True, camera=Camera(), input_router=router)
    env.configure_fast_touch(Detector())

    env.capture_camera_frame()
    event = env.poll_fast_touch()

    assert event is not None
    assert event.event_type is InputEventType.TOUCH_BEGIN
    assert event.device_id == "vigil.visual-pointer"
    assert event.metadata["source"] == "vigil-visual-pointer"
    assert router.raw_events == (event,)
