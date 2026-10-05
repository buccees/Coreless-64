"""Coreless-native VIGIL environment lifecycle."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .world import WorldModel
from .tracking import TrackManager
from .priority import RelevancePriorityEngine
from .attention import AttentionManager
from .interaction import HumanInteractionService
from .input import VigilInputLayer


@dataclass(frozen=True)
class VigilStatus:
    enabled: bool
    camera_available: bool
    world_entities: int
    tracks: int
    attention_items: int


class VigilEnvironment:
    """Complete optional VIGIL environment hosted by Coreless."""

    VERSION = 1

    def __init__(self, *, enabled: bool = False, input_layer: VigilInputLayer | None = None) -> None:
        self.enabled = enabled
        self.input = input_layer or VigilInputLayer(enabled=enabled)
        self.world = WorldModel()
        self.tracking = TrackManager()
        self.priority = RelevancePriorityEngine()
        self.attention = AttentionManager()
        self.interaction = HumanInteractionService()

    def enable(self) -> None:
        self.enabled = True
        self.input.enable(True)

    def disable(self) -> None:
        self.enabled = False
        self.input.enable(False)

    def status(self) -> VigilStatus:
        return VigilStatus(
            enabled=self.enabled,
            camera_available=self.input.camera is not None and self.input.camera.available(),
            world_entities=len(self.world.entities()),
            tracks=len(self.tracking.tracks()),
            attention_items=len(self.attention.items()),
        )

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "input": self.input.persistent_state(),
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", self.VERSION)) != self.VERSION:
            raise ValueError("unsupported VIGIL environment state version")
        self.enabled = bool(state.get("enabled", False))
        input_state = state.get("input", {})
        if isinstance(input_state, Mapping):
            self.input.restore_state(input_state)
        self.input.enable(self.enabled)
