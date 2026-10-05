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
