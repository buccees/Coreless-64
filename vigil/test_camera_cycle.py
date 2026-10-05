from vigil.runtime import VigilEnvironment
from vigil.model import Detection, EntityType, Provenance
from vigil.spatial import CameraFrame
from reference.input import CorelessInputRouter


class Camera:
    def __init__(self):
        self.reads = 0

    def available(self):
        return True

    def read(self):
        self.reads += 1
        return CameraFrame("camera-1", self.reads * 1_000_000, self.reads, 1920, 1080)


class TouchDetector:
    def detect(self, frame):
        return Detection(
            detection_id=f"touch-{frame.sequence}",
            observation_id=f"camera:camera-1:{frame.sequence}",
            entity_type=EntityType.PERSON,
            label="finger",
            timestamp_ns=frame.timestamp_ns,
            position=(100.0, 200.0, 0.0),
            confidence=0.95,
            uncertainty=None,
            provenance=(Provenance("camera-1", "camera", frame.timestamp_ns),),
        )


class PerceptionProvider:
    def __init__(self):
        self.sequences = []

    def detect(self, frame):
        self.sequences.append(frame.sequence)
        return ()


def test_one_camera_capture_feeds_touch_and_perception():
    camera = Camera()
    router = CorelessInputRouter()
    env = VigilEnvironment(enabled=True, camera=camera, input_router=router)
    env.configure_fast_touch(TouchDetector())
    provider = PerceptionProvider()

    cycle = env.run_camera_cycle(provider=provider)

    assert cycle.frame_sequence == 1
    assert cycle.touch_event is not None
    assert cycle.touch_event.metadata["source"] == "vigil-visual-pointer"
    assert cycle.perception is not None
    assert provider.sequences == [1]
    assert camera.reads == 1


def test_camera_cycle_without_optional_consumers_still_captures_once():
    camera = Camera()
    env = VigilEnvironment(enabled=True, camera=camera)

    cycle = env.run_camera_cycle()

    assert cycle.frame_sequence == 1
    assert cycle.touch_event is None
    assert cycle.perception is None
    assert camera.reads == 1
