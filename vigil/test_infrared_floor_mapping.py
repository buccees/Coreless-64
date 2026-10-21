import pytest

from vigil.infrared_floor_mapping import (
    InfraredFloorMapper,
    InfraredPixelSample,
)
from vigil.raster_calibration import RasterBlueprintCalibration, RasterControlPoint


def calibration():
    return RasterBlueprintCalibration.fit(
        model_id="facility",
        model_revision="r7",
        frame_id="facility/world",
        level_id="L1",
        elevation_m=2.5,
        control_points=[
            RasterControlPoint(0, 0, 0, 0, "origin"),
            RasterControlPoint(100, 0, 10, 0, "east"),
            RasterControlPoint(0, 100, 0, 10, "north"),
        ],
    )


def test_infrared_samples_project_into_calibrated_floor_coordinates():
    mapper = InfraredFloorMapper(
        calibration(), sensor_id="thermal-cam-1", image_width=200, image_height=150
    )
    result = mapper.map_frame(
        [
            InfraredPixelSample(25, 40, 0.8, temperature_c=31.5, label="warm-patch"),
            InfraredPixelSample(50, 50, 0.2),
        ],
        timestamp_ns=1234,
    )
    assert (result.model_id, result.model_revision, result.frame_id, result.level_id) == (
        "facility", "r7", "facility/world", "L1"
    )
    assert result.timestamp_ns == 1234
    assert result.samples[0].position_m == pytest.approx((2.5, 4.0, 2.5))
    assert result.samples[0].temperature_c == pytest.approx(31.5)
    assert result.samples[0].intensity == pytest.approx(0.8)
    assert result.samples[0].uncertainty_m == pytest.approx(0.1)
    assert result.samples[0].label == "warm-patch"


def test_infrared_mapping_rejects_bad_samples_and_out_of_frame_pixels():
    with pytest.raises(ValueError, match="normalized"):
        InfraredPixelSample(1, 1, 1.1)
    mapper = InfraredFloorMapper(
        calibration(), sensor_id="thermal-cam-1", image_width=10, image_height=10
    )
    with pytest.raises(ValueError, match="outside"):
        mapper.map_frame([InfraredPixelSample(10, 1, 0.5)], timestamp_ns=1)
    with pytest.raises(ValueError, match="timestamp_ns"):
        mapper.map_frame([], timestamp_ns=-1)


def test_infrared_mapper_validates_sensor_and_image_dimensions():
    with pytest.raises(ValueError, match="sensor_id"):
        InfraredFloorMapper(calibration(), sensor_id="", image_width=10, image_height=10)
    with pytest.raises(ValueError, match="image_width"):
        InfraredFloorMapper(calibration(), sensor_id="ir", image_width=0, image_height=10)
