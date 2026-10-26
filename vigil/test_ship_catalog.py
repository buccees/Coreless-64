import pytest

from vigil.ship_catalog import VESSEL_DIMENSIONS, get_vessel_dimensions


def test_real_vessel_dimensions_are_sourced_and_keep_distinct_scale():
    destroyer = get_vessel_dimensions("ddg51-flight-i-ii")
    carrier = get_vessel_dimensions("nimitz-cvn")

    assert destroyer.length_m == pytest.approx(153.92)
    assert destroyer.beam_m == pytest.approx(18.0)
    assert carrier.length_m == pytest.approx(332.85)
    assert carrier.beam_m == pytest.approx(40.84)
    assert destroyer.dimensions_source_url.startswith("https://www.navy.mil/")
    assert carrier.dimensions_source_url.startswith("https://www.navy.mil/")
    assert carrier.length_m > destroyer.length_m
    assert carrier.aspect_ratio == pytest.approx(332.85 / 40.84)


def test_catalog_does_not_misrepresent_dimension_sources_as_blueprints():
    assert VESSEL_DIMENSIONS
    assert all(record.plan_view_source_url is None for record in VESSEL_DIMENSIONS.values())
    assert all(not record.has_verified_plan_view for record in VESSEL_DIMENSIONS.values())


def test_unknown_vessel_does_not_silently_fall_back_to_generic_dimensions():
    with pytest.raises(KeyError, match="unknown vessel dimensions record"):
        get_vessel_dimensions("fictional-class")
