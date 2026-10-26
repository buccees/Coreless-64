"""Traceable real-vessel dimensions for the regional campaign model.

Dimensions come from official U.S. Navy fact sheets. These records are NOT
blueprint outlines: plan-view geometry remains explicitly unavailable until a
specific drawing is sourced and digitized with provenance/licensing checked.
Never render a generic polygon and label it a real blueprint.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VesselDimensions:
    vessel_id: str
    display_name: str
    ship_class: str
    length_m: float
    beam_m: float
    dimensions_source_url: str
    plan_view_source_url: str | None = None

    @property
    def aspect_ratio(self) -> float:
        return self.length_m / self.beam_m

    @property
    def has_verified_plan_view(self) -> bool:
        return bool(self.plan_view_source_url)


VESSEL_DIMENSIONS: dict[str, VesselDimensions] = {
    "ddg51-flight-i-ii": VesselDimensions(
        vessel_id="ddg51-flight-i-ii",
        display_name="Arleigh Burke-class destroyer (Flights I/II)",
        ship_class="destroyer",
        length_m=153.92,
        beam_m=18.0,
        dimensions_source_url=(
            "https://www.navy.mil/Resources/Fact-Files/Display-FactFiles/"
            "Article/2169871/destroyers-ddg-51/"
        ),
    ),
    "nimitz-cvn": VesselDimensions(
        vessel_id="nimitz-cvn",
        display_name="Nimitz-class aircraft carrier",
        ship_class="carrier",
        length_m=332.85,
        beam_m=40.84,
        dimensions_source_url=(
            "https://www.navy.mil/Resources/Fact-Files/Display-FactFiles/article/2169795/"
        ),
    ),
}


def get_vessel_dimensions(vessel_id: str) -> VesselDimensions:
    """Return a known sourced dimensions record; never invent a fallback."""
    try:
        return VESSEL_DIMENSIONS[vessel_id]
    except KeyError as exc:
        raise KeyError(f"unknown vessel dimensions record: {vessel_id}") from exc
