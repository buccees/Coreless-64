"""Blueprint registry and operator-facing spatial-scan workflow.

The workspace coordinates manifest import, active model/revision selection,
floor selection, observation ingestion, pose estimation, and terminal rendering.
It does not parse raw CAD/PDF files or own hardware sensor drivers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate, load_blueprint_json
from .blueprint_view import BlueprintView, build_blueprint_view
from .building import BuildingBlueprint, FloorTracker, FloorTransition
from .positioning import PoseEstimator, SpatialObservation
from .terminal import VigilTerminal


@dataclass(frozen=True)
class WorkspaceSnapshot:
    model: BlueprintModel | None
    pose: PoseEstimate | None
    selected_level: str | None
    observation_count: int
    floor_transition: FloorTransition | None = None


class BlueprintRegistry:
    """In-memory registry keyed by model ID and revision."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], BlueprintModel] = {}
        self._active_key: tuple[str, str] | None = None

    @property
    def active_model(self) -> BlueprintModel | None:
        return self._models.get(self._active_key) if self._active_key else None

    @property
    def models(self) -> tuple[BlueprintModel, ...]:
        return tuple(self._models[key] for key in sorted(self._models))

    def register(self, model: BlueprintModel, *, activate: bool = False) -> BlueprintModel:
        if not isinstance(model, BlueprintModel):
            raise TypeError("model must be a validated BlueprintModel")
        key = (model.model_id, model.revision)
        previous = self._models.get(key)
        if previous is not None and previous.source_sha256 != model.source_sha256:
            raise ValueError("model ID and revision already exist with different content")
        self._models[key] = model
        if activate or self._active_key is None:
            self._active_key = key
        return model

    def import_json(self, document: str | bytes, *, activate: bool = False,
                    max_bytes: int = 5_000_000) -> BlueprintModel:
        model = load_blueprint_json(document, max_bytes=max_bytes)
        return self.register(model, activate=activate)

    def activate(self, model_id: str, revision: str | None = None) -> BlueprintModel:
        matches = [
            key for key in self._models
            if key[0] == model_id and (revision is None or key[1] == revision)
        ]
        if not matches:
            raise KeyError(f"blueprint not registered: {model_id!r} revision={revision!r}")
        if revision is None and len(matches) > 1:
            raise ValueError("multiple revisions are registered; specify revision explicitly")
        key = matches[0]
        self._active_key = key
        return self._models[key]


class SpatialWorkspace:
    """Small deterministic API boundary for a blueprint scan session."""

    def __init__(
        self,
        *,
        registry: BlueprintRegistry | None = None,
        estimator: PoseEstimator | None = None,
        terminal: VigilTerminal | None = None,
        max_observations: int = 512,
    ) -> None:
        if max_observations < 1:
            raise ValueError("max_observations must be positive")
        self.registry = registry or BlueprintRegistry()
        self.estimator = estimator or PoseEstimator()
        self.terminal = terminal or VigilTerminal()
        self.max_observations = max_observations
        self._observations: list[SpatialObservation] = []
        self._pose: PoseEstimate | None = None
        self._selected_level: str | None = None
        self._floor_tracker: FloorTracker | None = None
        self._last_floor_pose_timestamp_ns: int | None = None
        self._last_floor_transition: FloorTransition | None = None

    @property
    def active_model(self) -> BlueprintModel | None:
        return self.registry.active_model

    @property
    def selected_level(self) -> str | None:
        return self._selected_level

    @property
    def floor_transition(self) -> FloorTransition | None:
        return self._last_floor_transition

    def activate_building(self, building: BuildingBlueprint, *, starting_level: str) -> BlueprintModel:
        """Activate a composed building and initialize automatic floor tracking."""
        model = self.registry.register(building.model, activate=True)
        self._pose = None
        self._selected_level = None
        self._floor_tracker = FloorTracker(building)
        self._floor_tracker.establish_start(starting_level)
        self._selected_level = starting_level
        self._last_floor_pose_timestamp_ns = None
        self._last_floor_transition = FloorTransition(
            starting_level, None, False, "starting floor established"
        )
        return model

    def import_blueprint(self, document: str | bytes, *, activate: bool = False,
                         max_bytes: int = 5_000_000) -> BlueprintModel:
        previous_active = self.registry.active_model
        model = self.registry.import_json(document, activate=activate, max_bytes=max_bytes)
        if activate or previous_active is None:
            self._pose = None
            self._selected_level = None
            self._floor_tracker = None
            self._last_floor_pose_timestamp_ns = None
            self._last_floor_transition = None
        return model

    def activate_blueprint(self, model_id: str, revision: str | None = None) -> BlueprintModel:
        model = self.registry.activate(model_id, revision)
        self._pose = None
        self._selected_level = None
        self._floor_tracker = None
        self._last_floor_pose_timestamp_ns = None
        self._last_floor_transition = None
        return model

    def select_level(self, level: str) -> str:
        model = self.active_model
        if model is None:
            raise RuntimeError("register and activate a blueprint before selecting a level")
        normalized = level.strip()
        if not normalized:
            raise ValueError("level must not be empty")
        levels = {feature.level for feature in model.features if feature.level is not None}
        if normalized not in levels:
            raise KeyError(f"level not found in active blueprint: {normalized!r}")
        self._selected_level = normalized
        if self._floor_tracker is not None:
            # A manual floor choice resets the starting hypothesis; subsequent
            # transitions still require calibrated, repeated connector evidence.
            self._floor_tracker.establish_start(normalized)
            self._last_floor_pose_timestamp_ns = None
            self._last_floor_transition = FloorTransition(
                normalized, None, False, "starting floor reset manually"
            )
        return normalized

    def ingest(self, observations: Sequence[SpatialObservation]) -> int:
        """Append already-calibrated observations; returns accepted count.

        Observations are not transformed implicitly. Frame/revision alignment is
        enforced by PoseEstimator before any observation contributes to a pose.
        """
        accepted = 0
        for observation in observations:
            if not isinstance(observation, SpatialObservation):
                raise TypeError("all observations must be SpatialObservation instances")
            self._observations.append(observation)
            accepted += 1
        if len(self._observations) > self.max_observations:
            del self._observations[:-self.max_observations]
        return accepted

    def refresh(self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
                max_uncertainty_m: float = 5.0,
                max_disagreement_m: float = 2.0) -> WorkspaceSnapshot:
        model = self.active_model
        if model is None:
            self._pose = None
        else:
            self._pose = self.estimator.update(
                model, self._observations, now_ns=now_ns, max_age_ns=max_age_ns,
                max_uncertainty_m=max_uncertainty_m,
                max_disagreement_m=max_disagreement_m,
            )
            if self._floor_tracker is not None:
                timestamp = self._pose.observation_timestamp_ns
                pose_is_usable = (
                    self._pose.position_m is not None
                    and self._pose.uncertainty_m is not None
                    and self._pose.state.value in ("TRACKING", "DEGRADED")
                )
                # Repeated refreshes must not count one pose twice. Conversely,
                # an unavailable/stale pose must clear pending transition evidence.
                if not pose_is_usable or timestamp != self._last_floor_pose_timestamp_ns:
                    self._last_floor_transition = self._floor_tracker.update(self._pose)
                    self._last_floor_pose_timestamp_ns = timestamp
                    if self._last_floor_transition.changed:
                        self._selected_level = self._last_floor_transition.active_level
        return WorkspaceSnapshot(
            model, self._pose, self._selected_level, len(self._observations),
            self._last_floor_transition,
        )

    def blueprint_view(
        self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0, max_disagreement_m: float = 2.0,
    ) -> BlueprintView:
        """Return geometry and pose overlay for the current selected floor."""
        snapshot = self.refresh(
            now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
            max_disagreement_m=max_disagreement_m,
        )
        if snapshot.model is None:
            raise RuntimeError("register and activate a blueprint before building its view")
        return build_blueprint_view(
            snapshot.model, snapshot.pose, selected_level=snapshot.selected_level
        )

    def render(self, *, now_ns: int) -> str:
        snapshot = self.refresh(now_ns=now_ns)
        return self.terminal.render(
            snapshot.model, snapshot.pose, self._observations, now_ns=now_ns,
            selected_level=snapshot.selected_level,
        )
