from vigil.camera import SharedCameraSource
from vigil.spatial import CameraFrame


class Camera:
    def __init__(self):
        self.reads = 0

    def available(self):
        return True

    def read(self):
        self.reads += 1
        return CameraFrame("cam", self.reads, self.reads, 640, 480)


def test_shared_camera_has_one_physical_reader_and_shared_latest_frame():
    physical = Camera()
    shared = SharedCameraSource(physical)

    first = shared.capture()
    assert first.sequence == 1
    assert shared.latest() is first
    assert physical.reads == 1

    assert shared.latest() is first
    assert physical.reads == 1

    second = shared.capture()
    assert second.sequence == 2
    assert shared.latest() is second
    assert physical.reads == 2


def test_shared_camera_can_be_used_as_a_camera_source():
    physical = Camera()
    shared = SharedCameraSource(physical)

    assert shared.available()
    frame = shared.poll()
    assert frame is shared.latest()


def test_shared_camera_restores_sequence_watermark_without_fabricating_a_frame():
    physical = Camera()
    shared = SharedCameraSource(physical)
    shared.capture()
    state = shared.persistent_state()
    restored = SharedCameraSource(physical)
    restored.restore_state(state)
    assert restored.latest() is None
    assert restored.persistent_state()["last_sequence"] == 1
    try:
        restored.capture()
    except ValueError as exc:
        assert "monotonically" in str(exc)
    else:
        raise AssertionError("restored camera accepted a stale sequence")
