"""Explicit physical/logical arrangement for the Coreless autonomous core.

The canonical composition is five autonomous component slots:
two components in the enclosure/box and three components in a linear core.
AI is attached to the core as a coordinating capability, not as a host-owned
compute resource.

This module is deliberately topology-only. Component execution, dispatch,
identity, and AI authorization remain owned by the existing Coreless
component and Hub boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TopologyZone(str, Enum):
    """Canonical placement zones."""

    BOX = "box"
    CORE = "core"


@dataclass(frozen=True)
class TopologySlot:
    """One stable position in the canonical Coreless composition."""

    slot_id: str
    zone: TopologyZone
    position: int
    ai_attached: bool = False

    def __post_init__(self) -> None:
        if not self.slot_id:
            raise ValueError("slot_id must not be empty")
        if self.position < 0:
            raise ValueError("position must be non-negative")
        if self.zone is TopologyZone.BOX and self.ai_attached:
            raise ValueError("AI attachment belongs to the core, not a box slot")


@dataclass(frozen=True)
class CorelessTopology:
    """Canonical 2-in-box / 3-in-row core arrangement."""

    slots: tuple[TopologySlot, ...]
    ai_slot_id: str = "core-ai"

    BOX_COUNT = 2
    CORE_COUNT = 3

    @classmethod
    def canonical(cls) -> "CorelessTopology":
        return cls(
            slots=(
                TopologySlot("box-0", TopologyZone.BOX, 0),
                TopologySlot("box-1", TopologyZone.BOX, 1),
                TopologySlot("core-0", TopologyZone.CORE, 0, True),
                TopologySlot("core-1", TopologyZone.CORE, 1, True),
                TopologySlot("core-2", TopologyZone.CORE, 2, True),
            )
        )

    def validate(self) -> None:
        """Enforce the canonical topology without constraining component roles."""
        if len(self.slots) != self.BOX_COUNT + self.CORE_COUNT:
            raise ValueError("Coreless topology requires exactly five component slots")

        box = tuple(slot for slot in self.slots if slot.zone is TopologyZone.BOX)
        core = tuple(slot for slot in self.slots if slot.zone is TopologyZone.CORE)

        if len(box) != self.BOX_COUNT:
            raise ValueError("Coreless topology requires exactly two box components")
        if len(core) != self.CORE_COUNT:
            raise ValueError("Coreless topology requires exactly three core components")

        if {slot.position for slot in box} != {0, 1}:
            raise ValueError("box positions must be exactly 0 and 1")
        if {slot.position for slot in core} != {0, 1, 2}:
            raise ValueError("core positions must be exactly 0, 1 and 2")

        ids = [slot.slot_id for slot in self.slots]
        if len(ids) != len(set(ids)):
            raise ValueError("topology slot IDs must be unique")

        ai_slots = tuple(slot for slot in core if slot.ai_attached)
        if len(ai_slots) != self.CORE_COUNT:
            raise ValueError("AI must be integrated across the three core positions")

    @property
    def box_slots(self) -> tuple[TopologySlot, ...]:
        return tuple(
            sorted(
                (slot for slot in self.slots if slot.zone is TopologyZone.BOX),
                key=lambda slot: slot.position,
            )
        )

    @property
    def core_slots(self) -> tuple[TopologySlot, ...]:
        return tuple(
            sorted(
                (slot for slot in self.slots if slot.zone is TopologyZone.CORE),
                key=lambda slot: slot.position,
            )
        )

    def slot(self, slot_id: str) -> TopologySlot:
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(f"unknown topology slot: {slot_id}")

    def composition(self) -> dict[str, object]:
        """Return a stable machine-readable topology description."""
        self.validate()
        return {
            "box": tuple(slot.slot_id for slot in self.box_slots),
            "core": tuple(slot.slot_id for slot in self.core_slots),
            "core_layout": "linear",
            "ai_integrated": True,
            "ai_positions": tuple(slot.position for slot in self.core_slots),
        }
