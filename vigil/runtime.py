"""Coreless-native VIGIL environment lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ai.registry import AICoreRegistry
from reference.input import CorelessInputRouter
from reference.visual_input import VisualPointingDeviceAdapter

from .ai import CorelessVigilAI
from .attention import AttentionManager
from .camera import CameraReader, SharedCameraSource
from .fast_touch import FastCameraTouchPath, FastTouchDetector
from .input import VigilInputLayer
from .interaction import HumanInteractionService
from .presentation import PresentationManager
from .priority import RelevancePriorityEngine
from .perception import CameraPerceptionProvider, PerceptionPipeline, PerceptionResult
from .priority import PriorityContext
from .security import AuthorizationService
from .tracking import TrackManager
from .world import WorldModel


@dataclass(frozen=True)
class VigilCycleResult:
    frame_sequence: int
    touch_event: object | None
    perception: PerceptionResult | None
    priority: tuple[object, ...] = ()
    attention: tuple[object, ...] = ()
    presentation: object | None = None


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

    VERSION = 4

    def __init__(
        self,
        *,
        enabled: bool = False,
        input_layer: VigilInputLayer | None = None,
        ai_registry: AICoreRegistry | None = None,
        camera: CameraReader | None = None,
        input_router: CorelessInputRouter | None = None,
    ) -> None:
        self.enabled = enabled
        self.input = input_layer or VigilInputLayer(enabled=enabled)
        self.camera = SharedCameraSource(camera) if camera is not None else None
        self.input_router = input_router
        self.visual_input: VisualPointingDeviceAdapter | None = None
        self.fast_touch: FastCameraTouchPath | None = None
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

    def configure_fast_touch(
        self,
        detector: FastTouchDetector,
        *,
        input_router: CorelessInputRouter | None = None,
        display_width: int | None = None,
        display_height: int | None = None,
    ) -> FastCameraTouchPath:
        if self.camera is None:
            raise RuntimeError("VIGIL fast touch requires a camera")
        router = input_router or self.input_router
        if router is None:
            raise RuntimeError("VIGIL fast touch requires a Coreless input router")
        self.input_router = router
        self.visual_input = VisualPointingDeviceAdapter(router)
        self.visual_input.register_and_designate()
        self.fast_touch = FastCameraTouchPath(
            self.camera,
            detector,
            display_width=display_width,
            display_height=display_height,
        )
        return self.fast_touch

    def poll_fast_touch(self):
        if not self.enabled or self.fast_touch is None or self.visual_input is None:
            return None
        intent = self.fast_touch.poll()
        if intent is None:
            return None
        return self.visual_input.submit(intent)

    def capture_camera_frame(self):
        if not self.enabled or self.camera is None:
            return None
        return self.camera.capture()

    def run_camera_cycle(
        self,
        *,
        provider: CameraPerceptionProvider | None = None,
        priority_context: PriorityContext | None = None,
    ) -> VigilCycleResult | None:
        """Capture once, then fan the same frame into fast touch and perception."""
        if not self.enabled or self.camera is None:
            return None
        frame = self.camera.capture()
        if frame is None:
            return None

        touch_event = None
        if self.fast_touch is not None and self.visual_input is not None:
            intent = self.fast_touch.process_frame(frame)
            if intent is not None:
                touch_event = self.visual_input.submit(intent)

        perception_result = None
        if provider is not None:
            perception_result = self.perception.ingest_camera_frame(frame, provider)

        context = priority_context or PriorityContext(timestamp_ns=frame.timestamp_ns)
        priority_results = tuple(
            self.priority.evaluate(entity, context)
            for entity in self.world.entities()
        )
        ordered_priority = self.priority.order(priority_results)
        attention_items = self.attention.evaluate(ordered_priority)
        presentation_state = self.presentation.present(attention_items, frame.timestamp_ns)

        return VigilCycleResult(
            frame_sequence=frame.sequence,
            touch_event=touch_event,
            perception=perception_result,
            priority=ordered_priority,
            attention=attention_items,
            presentation=presentation_state,
        )

    def ingest_camera_frame(
        self,
        provider: CameraPerceptionProvider,
    ) -> PerceptionResult | None:
        if not self.enabled or self.camera is None:
            return None
        frame = self.camera.latest()
        if frame is None:
            return None
        return self.perception.ingest_camera_frame(frame, provider)

    def status(self) -> VigilStatus:
        return VigilStatus(
            enabled=self.enabled,
            camera_available=self.camera is not None and self.camera.available(),
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
            "camera": self.camera.persistent_state() if self.camera is not None else None,
            "fast_touch_enabled": self.fast_touch is not None,
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", self.VERSION)) != self.VERSION:
            raise ValueError("unsupported VIGIL environment state version")
        self.enabled = bool(state.get("enabled", False))
        input_state = state.get("input", {})
        if isinstance(input_state, Mapping):
            self.input.restore_state(input_state)
        self.input.enable(self.enabled)
