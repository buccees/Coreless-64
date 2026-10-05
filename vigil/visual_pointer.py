"""Visual-cue pointer/touch bridge for Coreless-native VIGIL.

Camera perception proposes pointer/touch actions; Coreless remains responsible
for the actual input boundary and device routing. No second AI is introduced.
"""
from __future__ import annotations
from dataclasses import dataclass
from .model import Detection, EntityType

@dataclass(frozen=True)
class VisualTouchIntent:
    action: str
    x: float
    y: float
    timestamp_ns: int
    detection_id: str
    confidence: float
    source_id: str
    def __post_init__(self) -> None:
        if self.action not in {"move", "touch_begin", "touch_end"}:
            raise ValueError("unsupported visual touch action")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

class VisualPointer:
    """Turns visual hand/finger cues into deterministic Coreless input intents."""
    def __init__(self, *, min_confidence: float = 0.7) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        self.min_confidence = min_confidence
        self._active = False
    @property
    def active(self) -> bool:
        return self._active
    def update(self, detection: Detection) -> VisualTouchIntent | None:
        if detection.confidence < self.min_confidence or detection.position is None:
            return None
        if detection.entity_type not in {EntityType.PERSON, EntityType.TARGET, EntityType.OBJECT}:
            return None
        x, y, _ = detection.position
        label = (detection.label or "").lower()
        if not any(token in label for token in ("finger", "hand", "touch", "point", "tap")):
            return None
        action = "touch_begin" if not self._active else "move"
        self._active = True
        return VisualTouchIntent(action, x, y, detection.timestamp_ns, detection.detection_id,
                                 detection.confidence, detection.provenance[0].source_id if detection.provenance else "vigil")
    def release(self, detection: Detection) -> VisualTouchIntent | None:
        if not self._active or detection.position is None:
            return None
        self._active = False
        x, y, _ = detection.position
        return VisualTouchIntent("touch_end", x, y, detection.timestamp_ns, detection.detection_id,
                                 detection.confidence, detection.provenance[0].source_id if detection.provenance else "vigil")
