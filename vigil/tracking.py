"""Deterministic track continuity for VIGIL."""
from __future__ import annotations
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
