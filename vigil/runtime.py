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
from .interaction import HumanInteractionService, InputModality, InteractionRequest, InteractionResponse, VoiceInputSource
from .presentation import PresentationManager
from .priority import RelevancePriorityEngine
from .perception import CameraPerceptionProvider, PerceptionPipeline, PerceptionResult
from .priority import PriorityContext
from .provenance import EventProvenance
from .security import AuthorizationContext, AuthorizationService
from .simulation import ReplayEvent, ReplayLog, ReplayValidation
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

    VERSION = 5

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
        self.replay = ReplayLog()

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

    def poll_voice(
        self,
        source: VoiceInputSource,
        *,
        session_id: str,
        authorization_scope: str,
        required_scope: str,
        request_prefix: str = "voice",
    ) -> InteractionResponse | None:
        """Poll optional voice transport and route it through the same interaction path."""
        if not self.enabled or not source.available():
            return None
        sample = source.read()
        if sample is None:
            return None
        text, timestamp_ns = sample
        request = InteractionRequest(
            request_id=f"{request_prefix}-{timestamp_ns}",
            modality=InputModality.VOICE,
            text=text,
            timestamp_ns=timestamp_ns,
            session_id=session_id,
            authorization_scope=authorization_scope,
        )
        return self.handle_interaction(request, required_scope=required_scope)

    def handle_interaction(
        self,
        request: InteractionRequest,
        *,
        required_scope: str,
    ) -> InteractionResponse | None:
        """Route an authorized human request through the shared Coreless AI."""
        if not self.enabled:
            return None
        if not self.authorization.authorize(
            AuthorizationContext(request.session_id, frozenset({request.authorization_scope})),
            required_scope,
        ):
            raise PermissionError("VIGIL interaction is not authorized")
        analysis = self.ai.analyze(
            request.text,
            self.world.entities(),
            request_id=request.request_id,
        )
        if analysis is None:
            return None
        request_provenance = request.provenance
        provenance = request_provenance if isinstance(request_provenance, EventProvenance) else EventProvenance(
            source_type=f"interaction.{request.modality.value}",
            source_ids=(request.request_id,),
            timestamp_ns=request.timestamp_ns,
        )
        return self.interaction.respond(
            request,
            analysis.text,
            grounded=bool(analysis.grounded_entity_ids),
            timestamp_ns=request.timestamp_ns,
            source_entity_ids=analysis.grounded_entity_ids,
            provenance=provenance,
        )

    def ingest_input_event(self, event) -> tuple[object, ...]:
        """Record a Coreless raw input event and its VIGIL interpretations."""
        if not self.enabled or self.input_router is None:
            return ()
        device = next((item for item in self.input_router.devices.devices if item.device_id == event.device_id), None)
        if device is None:
            raise ValueError("input event references an unknown Coreless device")
        interpretations = self.input.interpret(event, device)
        self.replay.append(ReplayEvent(
            event_id=f"input-{event.sequence}",
            timestamp_ns=event.timestamp_ns,
            kind="input.raw",
            payload=event,
            provenance=EventProvenance(
                source_type="coreless-input",
                source_ids=(event.device_id,),
                source_sequences=(event.sequence,),
                timestamp_ns=event.timestamp_ns,
            ),
        ))
        for item in interpretations:
            self.replay.append(ReplayEvent(
                event_id=item.interpretation_id,
                timestamp_ns=item.timestamp_ns,
                kind=item.kind,
                payload=item,
                provenance=EventProvenance(
                    source_type=item.kind,
                    source_ids=(item.device_id,),
                    source_sequences=item.source_sequence,
                    timestamp_ns=item.timestamp_ns,
                    confidence=item.confidence,
                ),
            ))
        return interpretations

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
        self.replay.append(ReplayEvent(
            event_id=f"camera-frame-{frame.sequence}",
            timestamp_ns=frame.timestamp_ns,
            kind="camera.frame",
            payload=frame,
            provenance=EventProvenance(
                source_type="camera",
                source_ids=(frame.source_id,),
                source_sequences=(frame.sequence,),
                timestamp_ns=frame.timestamp_ns,
            ),
        ))

        touch_event = None
        if self.fast_touch is not None and self.visual_input is not None:
            intent = self.fast_touch.process_frame(frame)
            if intent is not None:
                touch_event = self.visual_input.submit(intent)
                self.replay.append(ReplayEvent(
                    event_id=f"visual-touch-{frame.sequence}",
                    timestamp_ns=intent.timestamp_ns,
                    kind="visual.touch",
                    payload=intent,
                    provenance=EventProvenance(
                        source_type="visual-touch",
                        source_ids=(intent.source_id, intent.detection_id),
                        source_sequences=(frame.sequence,),
                        timestamp_ns=intent.timestamp_ns,
                        confidence=intent.confidence,
                    ),
                ))

        perception_result = None
        if provider is not None:
            perception_result = self.perception.ingest_camera_frame(frame, provider)
            self.replay.append(ReplayEvent(
                event_id=f"perception-{frame.sequence}",
                timestamp_ns=frame.timestamp_ns,
                kind="camera.perception",
                payload=perception_result,
                provenance=EventProvenance(
                    source_type="camera.perception",
                    source_ids=(frame.source_id,),
                    source_sequences=(frame.sequence,),
                    timestamp_ns=frame.timestamp_ns,
                ),
            ))

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

    def replay_events(self, consumer=None) -> tuple[object, ...]:
        """Replay the recorded VIGIL session without live hardware."""
        if consumer is None:
            return self.replay.replay()
        return self.replay.replay_into(consumer)

    def replay_and_validate(self, consumer) -> ReplayValidation:
        """Replay a session and validate its event/provenance chain."""
        replayed = self.replay.replay_into(consumer)
        invalid = tuple(
            index for index, item in enumerate(replayed)
            if not isinstance(item, ReplayEvent)
        )
        if invalid:
            return ReplayValidation(
                valid=False,
                event_count=len(replayed),
                mismatches=tuple(
                    f"replay[{index}]: consumer returned non-ReplayEvent"
                    for index in invalid
                ),
            )
        return self.replay.validate_replay(tuple(replayed))

    def validate_persisted_replay_integrity(self) -> ReplayValidation:
        """Validate the current replay chain against its persisted integrity record."""
        return self.replay.verify_integrity(self.replay.integrity_record())

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
            "world": self.world.persistent_state(),
            "tracking": self.tracking.persistent_state(),
            "attention": self.attention.persistent_state(),
            "interaction": self.interaction.persistent_state(),
            "replay": self.replay.persistent_state(),
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", self.VERSION)) != self.VERSION:
            raise ValueError("unsupported VIGIL environment state version")
        self.enabled = bool(state.get("enabled", False))
        replay_state = state.get("replay")
        if replay_state is not None:
            self.replay = ReplayLog.from_persistent_state(replay_state)
        else:
            replay_integrity = state.get("replay_integrity")
            if isinstance(replay_integrity, Mapping):
                result = self.replay.verify_integrity(replay_integrity)
                if not result.valid:
                    raise ValueError(
                        "VIGIL replay integrity verification failed: "
                        + "; ".join(result.mismatches)
                    )
        input_state = state.get("input", {})
        if isinstance(input_state, Mapping):
            self.input.restore_state(input_state)
        world_state = state.get("world")
        if isinstance(world_state, Mapping):
            self.world.restore_state(world_state)
        tracking_state = state.get("tracking")
        if isinstance(tracking_state, Mapping):
            self.tracking.restore_state(tracking_state)
        attention_state = state.get("attention")
        if isinstance(attention_state, Mapping):
            self.attention.restore_state(attention_state)
        interaction_state = state.get("interaction")
        if isinstance(interaction_state, Mapping):
            self.interaction.restore_state(interaction_state)
        self.input.enable(self.enabled)
