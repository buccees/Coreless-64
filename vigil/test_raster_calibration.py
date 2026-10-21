import pytest

from vigil.raster_calibration import RasterBlueprintCalibration, RasterControlPoint


def test_affine_raster_calibration_maps_pixels_into_floor_model_coordinates():
    points = [
        RasterControlPoint(0, 0, 1, 2, "origin"),
        RasterControlPoint(100, 0, 3, 3, "east"),
        RasterControlPoint(0, 100, 0, 4, "north"),
        RasterControlPoint(100, 100, 2, 5, "corner"),
    ]
    calibration = RasterBlueprintCalibration.fit(
        model_id="facility", model_revision="r3", frame_id="facility/world",
        level_id="L2", elevation_m=3.4, control_points=points,
    )
    assert calibration.control_point_count == 4
    assert calibration.rms_residual_m == pytest.approx(0, abs=1e-8)
    assert calibration.pixel_to_model(25, 50) == pytest.approx((1.0, 3.25, 3.4))
    pixel = calibration.model_to_pixel(1.0, 3.25)
    assert pixel == pytest.approx((25, 50))
    assert calibration.control_labels == ("origin", "east", "north", "corner")


def test_raster_calibration_rejects_insufficient_or_degenerate_control_points():
    with pytest.raises(ValueError, match="at least three"):
        RasterBlueprintCalibration.fit(
            model_id="site", model_revision="r1", frame_id="site/world",
            level_id="L1", elevation_m=0,
            control_points=[RasterControlPoint(0, 0, 0, 0), RasterControlPoint(1, 1, 1, 1)],
        )
    collinear = [
        RasterControlPoint(0, 0, 0, 0),
        RasterControlPoint(1, 1, 1, 2),
        RasterControlPoint(2, 2, 2, 4),
    ]
    with pytest.raises(ValueError, match="collinear or geometrically degenerate"):
        RasterBlueprintCalibration.fit(
            model_id="site", model_revision="r1", frame_id="site/world",
            level_id="L1", elevation_m=0, control_points=collinear,
        )


def test_raster_calibration_rejects_nonfinite_coordinates_and_bad_identity():
    with pytest.raises(ValueError, match="finite"):
        RasterControlPoint(float("nan"), 0, 0, 0)
    with pytest.raises(ValueError, match="IDs are required"):
        RasterBlueprintCalibration.fit(
            model_id="", model_revision="r1", frame_id="site/world",
            level_id="L1", elevation_m=0,
            control_points=[
                RasterControlPoint(0, 0, 0, 0),
                RasterControlPoint(1, 0, 1, 0),
                RasterControlPoint(0, 1, 0, 1),
            ],
        )
