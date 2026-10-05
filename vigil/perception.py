"""Coreless-native VIGIL perception pipeline.

This module is deliberately model-agnostic: perception providers produce the
same canonical Observation/Detection objects, then Coreless-owned tracking and
world-model services consume them deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from .spatial import CameraFrame

from .model import Detection, EntityType, Observation, Provenance, Track, Uncertainty, WorldEntity
from .tracking import TrackManager
from .world import WorldModel


@dataclass(frozen=True)
class PerceptionResult:
    observations: tuple[Observation, ...]
    detections: tuple[Detection, ...]
    tracks: tuple[Track, ...]
    world_entities: tuple[WorldEntity, ...]


class CameraPerceptionProvider(Protocol):
    """Optional detector boundary; implementations remain behind Coreless APIs."""

    def detect(self, frame: CameraFrame) -> tuple[Detection, ...]:
        ...


class PerceptionPipeline:
    """Canonical observation -> detection -> track -> world pipeline."""

    def __init__(self, *, tracking: TrackManager, world: WorldModel) -> None:
        self.tracking = tracking
        self.world = world

    def ingest_camera_frame(
        self,
        frame: CameraFrame,
        provider: CameraPerceptionProvider,
    ) -> PerceptionResult:
        """Convert one camera frame through the canonical perception boundary."""
        observation = Observation(
            observation_id=f"camera:{frame.source_id}:{frame.sequence}",
            source_id=frame.source_id,
            timestamp_ns=frame.timestamp_ns,
            payload={"width": frame.width, "height": frame.height, "sequence": frame.sequence},
            confidence=float(frame.metadata.get("confidence", 1.0)),
            provenance=Provenance(frame.source_id, "camera", frame.timestamp_ns, frame.metadata),
        )
        detections = tuple(provider.detect(frame))
        for detection in detections:
            if detection.observation_id != observation.observation_id:
                raise ValueError("camera detection must reference the current frame observation")
        return self.ingest((observation,), detections)

    def ingest(
        self,
        observations: Iterable[Observation],
        detections: Iterable[Detection],
    ) -> PerceptionResult:
        observations_tuple = tuple(sorted(observations, key=lambda item: (item.timestamp_ns, item.observation_id)))
        detections_tuple = tuple(sorted(detections, key=lambda item: (item.timestamp_ns, item.detection_id)))
        tracks: list[Track] = []
        entities: list[WorldEntity] = []

        for detection in detections_tuple:
            track = self.tracking.update(detection)
            tracks.append(track)
            provenance = detection.provenance
            if not provenance:
                observation = next(
                    (item for item in observations_tuple if item.observation_id == detection.observation_id),
                    None,
                )
                if observation is not None and observation.provenance is not None:
                    provenance = (observation.provenance,)
            entity = WorldEntity(
                entity_id=f"entity:{track.track_id}",
                entity_type=detection.entity_type,
                label=detection.label,
                position=detection.position,
                track_id=track.track_id,
                confidence=detection.confidence,
                uncertainty=detection.uncertainty,
                provenance=provenance,
                first_seen_ns=track.last_timestamp_ns if not track.detection_ids[:-1] else self._first_seen(track),
                last_seen_ns=detection.timestamp_ns,
                metadata={"detection_id": detection.detection_id},
            )
            entities.append(entity)

        for entity in entities:
            self.world.upsert(
                entity,
                event_id=f"perception:{entity.entity_id}:{entity.last_seen_ns}",
                timestamp_ns=entity.last_seen_ns,
            )

        return PerceptionResult(
            observations=observations_tuple,
            detections=detections_tuple,
            tracks=tuple(tracks),
            world_entities=tuple(entities),
        )

    @staticmethod
    def _first_seen(track: Track) -> int:
        # The track manager currently retains detection IDs but not their full
        # timestamps; the first observable timestamp is therefore the track's
        # current timestamp until historical detection storage is introduced.
        return track.last_timestamp_ns


def detection_from_observation(
    observation: Observation,
    *,
    entity_type: EntityType = EntityType.UNKNOWN,
    label: str | None = None,
    position: tuple[float, float, float] | None = None,
    confidence: float | None = None,
    uncertainty: Uncertainty | None = None,
) -> Detection:
    """Create a canonical detection without binding VIGIL to a vision library."""
    return Detection(
        detection_id=f"detection:{observation.observation_id}",
        observation_id=observation.observation_id,
        entity_type=entity_type,
        label=label,
        timestamp_ns=observation.timestamp_ns,
        position=position,
        confidence=observation.confidence if confidence is None else confidence,
        uncertainty=observation.uncertainty if uncertainty is None else uncertainty,
        provenance=() if observation.provenance is None else (observation.provenance,),
    )
