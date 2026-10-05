from vigil.model import Detection, EntityType, Provenance
from vigil.priority import PriorityContext
from vigil.runtime import VigilEnvironment
from vigil.spatial import CameraFrame


class FakeCamera:
    def __init__(self):
        self.frames = [
            CameraFrame("cam", 100, 1, 640, 480),
        ]
    def available(self):
        return bool(self.frames)
    def read(self):
        return self.frames.pop(0) if self.frames else None


class Provider:
    def detect(self, frame):
        return (
            Detection(
                "d1",
                f"{frame.source_id}:{frame.sequence}",
                EntityType.OBJECT,
                "target",
                frame.timestamp_ns,
                position=(1.0, 0.0, 0.0),
                confidence=1.0,
                provenance=(Provenance(frame.source_id, "camera", frame.timestamp_ns),),
            ),
        )


def test_camera_cycle_drives_perception_priority_attention_and_presentation():
    environment = VigilEnvironment(enabled=True, camera=FakeCamera())
    result = environment.run_camera_cycle(
        provider=Provider(),
        priority_context=PriorityContext(100, reference_position=(0.0, 0.0, 0.0)),
    )

    assert result is not None
    assert result.frame_sequence == 1
    assert result.perception is not None
    assert len(result.priority) == 1
    assert result.priority[0].world_entity_id == "d1"
    assert len(result.attention) == 1
    assert result.attention[0].world_entity_id == "d1"
    assert result.presentation is not None
    assert result.presentation.items[0].world_entity_id == "d1"


def test_camera_cycle_still_works_without_perception_provider():
    environment = VigilEnvironment(enabled=True, camera=FakeCamera())
    result = environment.run_camera_cycle()

    assert result is not None
    assert result.perception is None
    assert result.priority == ()
    assert result.attention == ()
    assert result.presentation is not None
