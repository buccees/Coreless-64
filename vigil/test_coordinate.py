from vigil.coordinate import CameraDisplayMapper


def test_camera_coordinates_map_to_display():
    mapper = CameraDisplayMapper(1920, 1080, 1280, 720)
    assert mapper.map(960, 540) == (640.0, 360.0)
    assert mapper.map(0, 0) == (0.0, 0.0)


def test_camera_coordinates_are_clamped():
    mapper = CameraDisplayMapper(100, 100, 200, 200)
    assert mapper.map(-10, 120) == (0.0, 200.0)


def test_camera_coordinates_can_reject_out_of_range_values():
    mapper = CameraDisplayMapper(100, 100, 200, 200, clamp=False)
    try:
        mapper.map(-1, 50)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range coordinates must be rejected")
