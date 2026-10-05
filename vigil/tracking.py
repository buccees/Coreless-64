"""Deterministic track continuity for VIGIL."""
from __future__ import annotations
from typing import Mapping
from .model import Detection, Track
from .fusion import distance


class TrackManager:
    def __init__(self, association_distance: float = 1.0) -> None:
        if association_distance < 0:
            raise ValueError("association_distance must be non-negative")
        self.association_distance = association_distance
        self._tracks: dict[str, Track] = {}
        self._next_id = 1

    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks[key] for key in sorted(self._tracks))

    def update(self, detection: Detection) -> Track:
        candidates = [
            track for track in self._tracks.values()
            if detection.position is not None and track.position is not None
            and distance(detection.position, track.position) <= self.association_distance
        ]
        track = min(candidates, key=lambda value: value.track_id) if candidates else None
        if track is None:
            track = Track(
                track_id=f"track-{self._next_id}",
                detection_ids=(detection.detection_id,),
                last_timestamp_ns=detection.timestamp_ns,
                position=detection.position,
                confidence=detection.confidence,
            )
            self._next_id += 1
        else:
            dt = detection.timestamp_ns - track.last_timestamp_ns
            velocity = track.velocity
            if dt > 0 and track.position is not None and detection.position is not None:
                scale = 1_000_000_000 / dt
                velocity = tuple((detection.position[i] - track.position[i]) * scale for i in range(3))
            track = Track(
                track_id=track.track_id,
                detection_ids=track.detection_ids + (detection.detection_id,),
                last_timestamp_ns=detection.timestamp_ns,
                position=detection.position,
                confidence=detection.confidence,
                velocity=velocity,
            )
        self._tracks[track.track_id] = track
        return track

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": 1,
            "association_distance": self.association_distance,
            "next_id": self._next_id,
            "tracks": [
                {
                    "track_id": track.track_id,
                    "detection_ids": list(track.detection_ids),
                    "last_timestamp_ns": track.last_timestamp_ns,
                    "position": None if track.position is None else list(track.position),
                    "confidence": track.confidence,
                    "velocity": None if track.velocity is None else list(track.velocity),
                }
                for track in self.tracks()
            ],
        }

    def restore_state(self, state: object) -> None:
        if not isinstance(state, Mapping) or state.get("version") != 1:
            raise ValueError("unsupported tracking state version")
        tracks = state.get("tracks", [])
        if not isinstance(tracks, list):
            raise ValueError("tracking tracks must be a list")
        association_distance = float(state.get("association_distance", self.association_distance))
        next_id = int(state.get("next_id", 1))
        if association_distance < 0:
            raise ValueError("association_distance must be non-negative")
        if next_id < 1:
            raise ValueError("next_id must be positive")
        restored: dict[str, Track] = {}
        seen_ids: set[str] = set()
        for record in tracks:
            if not isinstance(record, Mapping):
                raise ValueError("tracking record must be a mapping")
            position = record.get("position")
            velocity = record.get("velocity")
            track_id = str(record["track_id"])
            if not track_id:
                raise ValueError("track_id must not be empty")
            if track_id in seen_ids:
                raise ValueError("duplicate track_id")
            detection_ids = tuple(str(item) for item in record["detection_ids"])
            if any(not item for item in detection_ids):
                raise ValueError("detection_ids must not contain empty IDs")
            position_values = None if position is None else tuple(float(item) for item in position)
            velocity_values = None if velocity is None else tuple(float(item) for item in velocity)
            if position_values is not None and len(position_values) != 3:
                raise ValueError("track position must have three coordinates")
            if velocity_values is not None and len(velocity_values) != 3:
                raise ValueError("track velocity must have three coordinates")
            seen_ids.add(track_id)
            restored[track_id] = Track(
                track_id=track_id,
                detection_ids=detection_ids,
                last_timestamp_ns=int(record["last_timestamp_ns"]),
                position=position_values,
                confidence=float(record["confidence"]),
                velocity=velocity_values,
            )
        self.association_distance = association_distance
        self._next_id = next_id
        self._tracks = restored
