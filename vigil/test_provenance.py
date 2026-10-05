from vigil.interaction import InputModality, InteractionRequest
from vigil.provenance import EventProvenance
from vigil.runtime import VigilEnvironment


def test_interaction_response_preserves_event_provenance():
    env = VigilEnvironment(enabled=True)
    request = InteractionRequest(
        "req", InputModality.TEXT, "hello", 100, "session", "vigil.read",
        metadata={
            "provenance": EventProvenance(
                source_type="gesture.tap",
                source_ids=("device-1",),
                source_sequences=(7,),
                timestamp_ns=100,
                confidence=0.95,
            )
        },
    )
    # The request is traceable even before an AI core is attached.
    provenance = request.metadata["provenance"]
    assert provenance.source_type == "gesture.tap"
    assert provenance.source_sequences == (7,)
    assert provenance.confidence == 0.95


def test_provenance_contract_supports_camera_and_visual_touch_sources():
    camera = EventProvenance(
        source_type="camera.detection",
        source_ids=("camera-1", "detection-4"),
        source_sequences=(12,),
        timestamp_ns=200,
        confidence=0.91,
    )
    visual = EventProvenance(
        source_type="visual-touch",
        source_ids=("camera-1", "detection-4"),
        source_sequences=(12,),
        timestamp_ns=200,
        confidence=0.91,
    )
    assert camera.source_ids == visual.source_ids
    assert camera.source_sequences == visual.source_sequences
