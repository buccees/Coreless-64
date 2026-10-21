"""Connected multi-floor blueprint composition and floor-transition inference.

Each uploaded floor is explicitly assigned a level, then transformed into one
building coordinate frame. Floor changes are inferred from calibrated pose
evidence; UI floor selection is not a runtime navigation lock.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping, Sequence

from .blueprint import BlueprintModel, CoordinateTransform, ModelFeature, PoseEstimate, register_blueprint


@dataclass(frozen=True)
class FloorRegistration:
    level_id: str
    label: str
    elevation_m: float
    local_frame_id: str
    transform_to_building: CoordinateTransform

    def __post_init__(self) -> None:
        if not self.level_id.strip() or not self.label.strip() or not self.local_frame_id.strip():
            raise ValueError("floor ID, label, and local frame are required")
        if not isfinite(self.elevation_m):
            raise ValueError("floor elevation must be finite")
        if self.transform_to_building.source_frame != self.local_frame_id:
            raise ValueError("floor transform source frame must match the registered local frame")


@dataclass(frozen=True)
class VerticalConnection:
    connection_id: str
    kind: str
    from_level: str
    to_level: str
    from_position_m: tuple[float, float, float]
    to_position_m: tuple[float, float, float]

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.connection_id, self.kind, self.from_level, self.to_level
        )):
            raise ValueError("vertical connection identifiers and kind are required")
        if self.from_level == self.to_level:
            raise ValueError("vertical connection must link two different levels")
        for point in (self.from_position_m, self.to_position_m):
            if len(point) != 3 or not all(isfinite(float(value)) for value in point):
                raise ValueError("connection endpoints must be finite 3D positions")


@dataclass(frozen=True)
class BuildingBlueprint:
    model: BlueprintModel
    floors: tuple[FloorRegistration, ...]
    connections: tuple[VerticalConnection, ...]

    def __post_init__(self) -> None:
        ids = [floor.level_id for floor in self.floors]
        if len(ids) != len(set(ids)):
            raise ValueError("floor IDs must be unique")
        known = set(ids)
        for connection in self.connections:
            if connection.from_level not in known or connection.to_level not in known:
                raise ValueError("vertical connection refers to an unregistered floor")
        feature_levels = {feature.level for feature in self.model.features}
        if not feature_levels.issubset(known | {None}):
            raise ValueError("building model contains an unregistered floor label")


class BuildingBlueprintBuilder:
    """Compose uploaded floor manifests into one shared building model frame."""

    def __init__(self, building_id: str, revision: str, building_frame_id: str) -> None:
        if not all(value.strip() for value in (building_id, revision, building_frame_id)):
            raise ValueError("building ID, revision, and frame are required")
        self.building_id = building_id
        self.revision = revision
        self.building_frame_id = building_frame_id
        self._floors: dict[str, tuple[FloorRegistration, BlueprintModel]] = {}
        self._connections: dict[str, VerticalConnection] = {}

    def add_floor(
        self,
        floor_model: BlueprintModel,
        *,
        level_id: str,
        label: str,
        elevation_m: float,
        transform_to_building: CoordinateTransform,
    ) -> FloorRegistration:
        """Register one uploaded floor and align its geometry to the building frame."""
        if level_id in self._floors:
            raise ValueError(f"floor already registered: {level_id}")
        if transform_to_building.source_frame != floor_model.frame_id:
            raise ValueError("floor transform source frame must match uploaded blueprint frame")
        if transform_to_building.target_frame != self.building_frame_id:
            raise ValueError("floor transform target must be the building coordinate frame")
        registration = FloorRegistration(
            level_id, label, elevation_m, floor_model.frame_id, transform_to_building
        )
        self._floors[level_id] = (registration, floor_model)
        return registration

    def connect_floors(self, connection: VerticalConnection) -> None:
        if connection.connection_id in self._connections:
            raise ValueError(f"connection already registered: {connection.connection_id}")
        if connection.from_level not in self._floors or connection.to_level not in self._floors:
            raise ValueError("register both floors before connecting them")
        self._connections[connection.connection_id] = connection

    def build(self) -> BuildingBlueprint:
        if not self._floors:
            raise ValueError("upload and assign at least one floor before building")
        features: list[Mapping[str, object]] = []
        for level_id in sorted(self._floors):
            registration, floor_model = self._floors[level_id]
            for feature in floor_model.features:
                point = registration.transform_to_building.apply(
                    feature.position_m, source_frame=floor_model.frame_id
                )
                features.append({
                    "feature_id": f"{level_id}:{feature.feature_id}",
                    "label": feature.label,
                    "position": point,
                    "feature_type": feature.feature_type,
                    "level": level_id,
                    "zone": feature.zone,
                })
        model = register_blueprint(
            self.building_id, self.revision, frame_id=self.building_frame_id, units="m",
            features=features,
            metadata={
                "kind": "connected-building",
                "floor_labels": {key: self._floors[key][0].label for key in sorted(self._floors)},
                "floor_elevations_m": {key: self._floors[key][0].elevation_m for key in sorted(self._floors)},
            },
        )
        return BuildingBlueprint(
            model=model,
            floors=tuple(self._floors[key][0] for key in sorted(self._floors)),
            connections=tuple(self._connections[key] for key in sorted(self._connections)),
        )


@dataclass(frozen=True)
class FloorTransition:
    active_level: str | None
    candidate_level: str | None
    changed: bool
    reason: str


class FloorTracker:
    """Infer the active floor from calibrated building-frame poses with hysteresis.

    A floor change requires repeated poses close to a registered vertical
    connection endpoint and close to the destination floor's elevation.
    Uncertain or off-connector poses never force a floor switch.
    """

    def __init__(
        self,
        building: BuildingBlueprint,
        *,
        endpoint_radius_m: float = 2.5,
        elevation_tolerance_m: float = 1.5,
        confirmations_required: int = 2,
    ) -> None:
        if not isfinite(endpoint_radius_m) or endpoint_radius_m <= 0:
            raise ValueError("endpoint_radius_m must be positive and finite")
        if not isfinite(elevation_tolerance_m) or elevation_tolerance_m <= 0:
            raise ValueError("elevation_tolerance_m must be positive and finite")
        if confirmations_required < 1:
            raise ValueError("confirmations_required must be positive")
        self.building = building
        self.endpoint_radius_m = endpoint_radius_m
        self.elevation_tolerance_m = elevation_tolerance_m
        self.confirmations_required = confirmations_required
        self.active_level: str | None = None
        self._candidate: str | None = None
        self._confirmations = 0

    def establish_start(self, level_id: str) -> str:
        if level_id not in {floor.level_id for floor in self.building.floors}:
            raise KeyError(f"unknown starting floor: {level_id}")
        self.active_level = level_id
        self._candidate = None
        self._confirmations = 0
        return level_id

    def update(self, pose: PoseEstimate) -> FloorTransition:
        model = self.building.model
        if (pose.model_id, pose.model_revision, pose.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("pose must be aligned to the connected building model")
        if pose.position_m is None or pose.uncertainty_m is None:
            self._reset_candidate()
            return FloorTransition(self.active_level, None, False, "pose unavailable")
        if pose.state.value not in ("TRACKING", "DEGRADED"):
            self._reset_candidate()
            return FloorTransition(self.active_level, None, False, "pose state is not usable")
        if pose.uncertainty_m > self.elevation_tolerance_m:
            self._reset_candidate()
            return FloorTransition(self.active_level, None, False, "pose uncertainty too high")
        if self.active_level is None:
            return FloorTransition(None, None, False, "starting floor not established")

        x, y, z = pose.position_m
        floors = {floor.level_id: floor for floor in self.building.floors}
        candidate = None
        for connection in self.building.connections:
            if connection.from_level == self.active_level:
                destination, endpoint = connection.to_level, connection.to_position_m
                source_endpoint = connection.from_position_m
            elif connection.to_level == self.active_level:
                destination, endpoint = connection.from_level, connection.from_position_m
                source_endpoint = connection.to_position_m
            else:
                continue
            distance = sqrt((x-endpoint[0])**2 + (y-endpoint[1])**2 + (z-endpoint[2])**2)
            source_distance = sqrt((x-source_endpoint[0])**2 + (y-source_endpoint[1])**2 + (z-source_endpoint[2])**2)
            destination_floor = floors[destination]
            if (distance <= self.endpoint_radius_m
                    and source_distance <= self.endpoint_radius_m + abs(z-endpoint[2])
                    and abs(z-destination_floor.elevation_m) <= self.elevation_tolerance_m):
                candidate = destination
                break

        if candidate is None:
            self._reset_candidate()
            return FloorTransition(self.active_level, None, False, "no supported connected-floor transition")
        if candidate == self._candidate:
            self._confirmations += 1
        else:
            self._candidate = candidate
            self._confirmations = 1
        if self._confirmations < self.confirmations_required:
            return FloorTransition(self.active_level, candidate, False, "confirming transition")
        previous = self.active_level
        self.active_level = candidate
        self._reset_candidate()
        return FloorTransition(self.active_level, candidate, previous != candidate, "vertical connection and pose agree")

    def _reset_candidate(self) -> None:
        self._candidate = None
        self._confirmations = 0
