from vigil.fast_touch import FastCameraTouchPath
from vigil.camera import SharedCameraSource
from vigil.model import Detection, EntityType, Provenance
from vigil.spatial import CameraFrame


class Camera:
    def __init__(self, frames):
        self.frames = list(frames)
        self.reads = 0

    def available(self):
        return bool(self.frames)

    def read(self):
        self.reads += 1
        return self.frames.pop(0)


class Detector:
    def __init__(self, detections):
        self.detections = list(detections)

    def detect(self, frame):
        return self.detections.pop(0)


def detection(seq, x=100.0, y=200.0):
    return Detection(
        detection_id=f"d{seq}",
        observation_id=f"o{seq}",
        entity_type=EntityType.PERSON,
        label="finger",
        timestamp_ns=seq * 1_000_000,
        position=(x, y, 0.0),
        confidence=0.95,
        uncertainty=None,
        provenance=(Provenance("camera-1", "camera", seq * 1_000_000),),
    )


def frame(seq):
    return CameraFrame("camera-1", seq * 1_000_000, seq, 1920, 1080)


def test_fast_path_bypasses_full_perception_and_emits_touch_sequence():
    path = FastCameraTouchPath(
        Camera([frame(1), frame(2), frame(3)]),
        Detector([detection(1), detection(2, 120, 220), None]),
    )

    begin = path.poll()
    move = path.poll()
    end = path.poll()

    assert begin.action == "touch_begin"
    assert move.action == "move"
    assert end.action == "touch_end"
    assert path.frames_processed == 3
    assert path.last_frame_sequence == 3


def test_unavailable_camera_does_not_invoke_detector():
    class NoReadDetector:
        def detect(self, frame):
            raise AssertionError("detector must not run")

    path = FastCameraTouchPath(Camera([]), NoReadDetector())
    assert path.poll() is None


def test_fast_path_consumes_shared_latest_frame_without_second_camera_read():
    physical = Camera([frame(1), frame(2)])
    shared = SharedCameraSource(physical)
    path = FastCameraTouchPath(shared, Detector([detection(1), detection(2, 120, 220)]))

    shared.capture()
    first = path.poll()
    shared.capture()
    second = path.poll()

    assert first.action == "touch_begin"
    assert second.action == "move"
    assert physical.reads == 2
