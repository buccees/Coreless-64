from __future__ import annotations

import pytest

from core_topology import CorelessTopology, TopologySlot, TopologyZone


def test_canonical_topology_has_two_box_and_three_linear_core_slots():
    topology = CorelessTopology.canonical()

    topology.validate()

    assert tuple(slot.slot_id for slot in topology.box_slots) == ("box-0", "box-1")
    assert tuple(slot.slot_id for slot in topology.core_slots) == (
        "core-0",
        "core-1",
        "core-2",
    )
    assert all(slot.ai_attached for slot in topology.core_slots)
    assert topology.composition() == {
        "box": ("box-0", "box-1"),
        "core": ("core-0", "core-1", "core-2"),
        "core_layout": "linear",
        "ai_integrated": True,
        "ai_positions": (0, 1, 2),
    }


def test_box_slots_cannot_claim_ai_attachment():
    with pytest.raises(ValueError, match="AI attachment belongs to the core"):
        TopologySlot("box-ai", TopologyZone.BOX, 0, True)


def test_topology_rejects_wrong_core_count():
    topology = CorelessTopology(
        slots=(
            TopologySlot("box-0", TopologyZone.BOX, 0),
            TopologySlot("box-1", TopologyZone.BOX, 1),
            TopologySlot("core-0", TopologyZone.CORE, 0, True),
        )
    )

    with pytest.raises(ValueError, match="exactly five"):
        topology.validate()


def test_topology_rejects_non_linear_core_positions():
    topology = CorelessTopology(
        slots=(
            TopologySlot("box-0", TopologyZone.BOX, 0),
            TopologySlot("box-1", TopologyZone.BOX, 1),
            TopologySlot("core-0", TopologyZone.CORE, 0, True),
            TopologySlot("core-2", TopologyZone.CORE, 2, True),
            TopologySlot("core-3", TopologyZone.CORE, 3, True),
        )
    )

    with pytest.raises(ValueError, match="core positions"):
        topology.validate()
