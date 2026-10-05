from vigil.model import Detection, EntityType, Provenance
from vigil.perception import PerceptionPipeline
from vigil.spatial import CameraFrame
from vigil.tracking import TrackManager
from vigil.world import WorldModel


class FakeCameraDetector:
    def detect(self, frame):
        return (Detection(
            detection_id=f"detection:{frame.sequence}",
            observation_id=f"camera:{frame.source_id}:{frame.sequence}",
            entity_type=EntityType.OBJECT,
            label="object",
            timestamp_ns=frame.timestamp_ns,
            position=(1.0, 2.0, 0.0),
            confidence=0.8,
            provenance=(Provenance(frame.source_id, "camera", frame.timestamp_ns),),
        ),)


def test_camera_frame_flows_into_canonical_perception_pipeline():
    world = WorldModel()
    pipeline = PerceptionPipeline(tracking=TrackManager(), world=world)
    frame = CameraFrame("camera-1", 100, 1, 640, 480)
    result = pipeline.ingest_camera_frame(frame, FakeCameraDetector())
    assert result.observations[0].observation_id == "camera:camera-1:1"
    assert result.detections[0].observation_id == result.observations[0].observation_id
    assert result.world_entities[0].entity_type == EntityType.OBJECT
