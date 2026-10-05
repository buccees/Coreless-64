from vigil.model import EntityType, Observation, Provenance
from vigil.perception import PerceptionPipeline, detection_from_observation
from vigil.tracking import TrackManager
from vigil.world import WorldModel


def test_perception_pipeline_builds_tracks_and_world_entities():
    observation = Observation(
        observation_id="obs-1",
        source_id="camera-1",
        timestamp_ns=100,
        confidence=0.9,
        provenance=Provenance("camera-1", "camera", 100),
    )
    detection = detection_from_observation(
        observation,
        entity_type=EntityType.PERSON,
        label="person",
        position=(1.0, 2.0, 0.0),
    )
    world = WorldModel()
    result = PerceptionPipeline(tracking=TrackManager(), world=world).ingest(
        (observation,),
        (detection,),
    )
    assert result.tracks[0].track_id == "track-1"
    assert result.world_entities[0].track_id == "track-1"
    assert world.get("entity:track-1") == result.world_entities[0]
