"""Coreless-native VIGIL environment lifecycle."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from ai.registry import AICoreRegistry
from .ai import CorelessVigilAI
from .attention import AttentionManager
from .input import VigilInputLayer
from .interaction import HumanInteractionService
from .presentation import PresentationManager
from .priority import RelevancePriorityEngine
from .perception import PerceptionPipeline
from .security import AuthorizationService
from .tracking import TrackManager
from .world import WorldModel


@dataclass(frozen=True)
class VigilStatus:
    enabled: bool
    camera_available: bool
    world_entities: int
    tracks: int
    attention_items: int
    ai_available: bool


class VigilEnvironment:
    """Complete optional VIGIL environment hosted by Coreless."""

    VERSION = 1

    def __init__(
        self,
        *,
        enabled: bool = False,
        input_layer: VigilInputLayer | None = None,
        ai_registry: AICoreRegistry | None = None,
    ) -> None:
        self.enabled = enabled
        self.input = input_layer or VigilInputLayer(enabled=enabled)
        self.world = WorldModel()
        self.tracking = TrackManager()
        self.perception = PerceptionPipeline(tracking=self.tracking, world=self.world)
        self.priority = RelevancePriorityEngine()
        self.attention = AttentionManager()
        self.presentation = PresentationManager()
        self.interaction = HumanInteractionService()
        self.authorization = AuthorizationService()
        self.ai = CorelessVigilAI(ai_registry)

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
            ai_available=self.ai.available(),
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
