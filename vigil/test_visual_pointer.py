from vigil.model import Detection, EntityType, Provenance
from vigil.visual_pointer import VisualPointer

def test_visual_cue_starts_and_moves_pointer_touch():
    pointer = VisualPointer(min_confidence=0.5)
    d = Detection("d1","o1",EntityType.PERSON,"finger",100,(100,200,0),0.9,
                   provenance=(Provenance("cam","camera",100),))
    assert pointer.update(d).action == "touch_begin"
    moved = pointer.update(Detection("d2","o2",EntityType.PERSON,"finger",200,(120,220,0),0.9,
                                     provenance=(Provenance("cam","camera",200),)))
    assert moved.action == "move" and moved.x == 120 and moved.y == 220

def test_visual_cue_can_release_touch():
    pointer = VisualPointer()
    d = Detection("d1","o1",EntityType.PERSON,"hand",100,(10,20,0),0.9,
                   provenance=(Provenance("cam","camera",100),))
    pointer.update(d)
    assert pointer.release(d).action == "touch_end"

def test_low_confidence_and_non_touch_cues_are_ignored():
    pointer = VisualPointer(min_confidence=0.8)
    assert pointer.update(Detection("d1","o1",EntityType.OBJECT,"chair",100,(1,2,0),0.5)) is None
