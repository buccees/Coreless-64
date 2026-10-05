from vigil.runtime import VigilEnvironment
from vigil.spatial import CameraFrame


class Camera:
    def __init__(self):
        self.reads = 0

    def available(self):
        return True

    def read(self):
        self.reads += 1
        return CameraFrame("camera", self.reads, self.reads, 640, 480)


def test_environment_owns_one_shared_camera_reader():
    camera = Camera()
    env = VigilEnvironment(enabled=True, camera=camera)

    frame = env.capture_camera_frame()
    assert frame.sequence == 1
    assert env.camera.latest() is frame
    assert camera.reads == 1

    assert env.camera.latest() is frame
    assert camera.reads == 1
