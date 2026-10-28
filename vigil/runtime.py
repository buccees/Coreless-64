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
        if self.input_router is not None:
            self.input_router.vigil = self.input
            self.input_router.enable_vigil(enabled)
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
        self._artifact_recovery_consumer = None
        self._artifact_recovery_unsubscribe = None
        self._artifact_recovery_report = None

    def configure_artifact_recovery(self, *, world_seed: str, bridge, resolve_unit_state):
        """Attach persistent artifact recovery to this environment's live replay log.

        The caller must supply the server-owned artifact bridge and a resolver
        for authoritative unit state. This method never accepts browser state.
        Calling it twice replaces the previous subscription.
        """
        from .artifact_replay_consumer import ArtifactReplayConsumer

        self.disable_artifact_recovery()
        consumer = ArtifactReplayConsumer(
            world_seed=world_seed,
            bridge=bridge,
            resolve_unit_state=resolve_unit_state,
        )
        unsubscribe = consumer.attach(self.replay)
        self._artifact_recovery_consumer = consumer
        self._artifact_recovery_unsubscribe = unsubscribe
        # Reconcile persisted lifecycle events immediately on startup/configuration.
        # Keep the report so callers can inspect unresolved failures and retry.
        self._artifact_recovery_report = consumer.reconcile_recorded_events(self.replay)
        return consumer

    def connect_authoritative_unit_lifecycle(self, lifecycle_source, *, resolve_unit_state):
        """Connect a server-owned lifecycle publisher to artifact recovery.

        The source must expose subscribe_lifecycle(callback), returning an
        unsubscribe callable. It must publish confirmed UNIT_SUNK or
        UNIT_REMOVED records containing event_id, timestamp_ns, and unit_id.
        The resolver must read server-owned state; browser-originated lifecycle
        events are never accepted here.
        """
        from collections.abc import Mapping
        import math

        subscribe = getattr(lifecycle_source, "subscribe_lifecycle", None)
        if not callable(subscribe):
            raise TypeError("lifecycle_source must expose subscribe_lifecycle(callback)")
        if not callable(resolve_unit_state):
            raise TypeError("resolve_unit_state must be callable")
        if self._artifact_recovery_consumer is None:
            raise RuntimeError("configure_artifact_recovery must run before lifecycle connection")

        def publish(event):
            if not isinstance(event, Mapping):
                raise ValueError("authoritative lifecycle event must be a mapping")
            kind = event.get("kind")
            if kind not in ("UNIT_SUNK", "UNIT_REMOVED"):
                return None
            if event.get("status") != "CONFIRMED":
                raise ValueError("unit lifecycle event must be confirmed")
            event_id, unit_id = event.get("event_id"), event.get("unit_id")
            timestamp_ns = event.get("timestamp_ns")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ValueError("lifecycle event requires event_id")
            if not isinstance(unit_id, str) or not unit_id.strip():
                raise ValueError("lifecycle event requires unit_id")
            if not isinstance(timestamp_ns, int) or isinstance(timestamp_ns, bool) or timestamp_ns < 0:
                raise ValueError("lifecycle event timestamp_ns must be a non-negative integer")
            state = resolve_unit_state(unit_id)
            if state is None and kind == "UNIT_REMOVED":
                # Removal publishers should include a server-generated final
                # state snapshot, because the active fleet may already omit it.
                state = event.get("final_unit_state")
            if not isinstance(state, Mapping):
                raise ValueError("authoritative lifecycle unit state is unavailable")
            if str(state.get("id", "")) != unit_id:
                raise ValueError("lifecycle unit ID does not match authoritative state")
            if kind == "UNIT_SUNK":
                if state.get("afloat") is not False:
                    raise ValueError("sinking lifecycle event requires a confirmed sunk state")
                return self.confirm_unit_sunk(
                    event_id=event_id, timestamp_ns=timestamp_ns,
                    unit_id=unit_id, authoritative_unit_state=state,
                )
            if state.get("unitType") != "submersible":
                raise ValueError("only submersible removal triggers artifact recovery")
            # Use the final state snapshot, not any client-provided coordinates.
            x, y = state.get("x"), state.get("y")
            if isinstance(x, bool) or isinstance(y, bool):
                raise ValueError("final unit coordinates must be numeric")
            try:
                x, y = float(x), float(y)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("final unit coordinates must be numeric") from exc
            if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
                raise ValueError("final unit coordinates must be normalized finite values")
            snapshot = dict(state)
            snapshot["x"], snapshot["y"] = x, y
            return self.confirm_unit_removed(
                event_id=event_id, timestamp_ns=timestamp_ns,
                unit_id=unit_id, authoritative_unit_state=snapshot,
            )

        unsubscribe = subscribe(publish)
        if not callable(unsubscribe):
            raise TypeError("subscribe_lifecycle must return an unsubscribe callable")
        previous = getattr(self, "_unit_lifecycle_unsubscribe", None)
        if callable(previous):
            previous()
        self._unit_lifecycle_unsubscribe = unsubscribe
        return unsubscribe

    def disconnect_authoritative_unit_lifecycle(self) -> None:
        """Detach the lifecycle publisher without deleting replay or artifact data."""
        unsubscribe = getattr(self, "_unit_lifecycle_unsubscribe", None)
        if callable(unsubscribe):
            unsubscribe()
        self._unit_lifecycle_unsubscribe = None

    def disable_artifact_recovery(self) -> None:
        """Detach artifact recovery without changing the artifact ledger."""
        unsubscribe = self._artifact_recovery_unsubscribe
        self._artifact_recovery_unsubscribe = None
        self._artifact_recovery_consumer = None
        if unsubscribe is not None:
            unsubscribe()

    def artifact_recovery_status(self) -> dict[str, object]:
        """Return the last startup/reconnect reconciliation report, if configured."""
        if self._artifact_recovery_consumer is None:
            return {"configured": False, "report": self._artifact_recovery_report}
        return {"configured": True, "report": self._artifact_recovery_report}

    def retry_artifact_recovery(self) -> dict[str, object]:
        """Retry all recorded sinking/removal transitions against the current ledger."""
        if self._artifact_recovery_consumer is None:
            raise RuntimeError("artifact recovery is not configured")
        self._artifact_recovery_report = self._artifact_recovery_consumer.reconcile_recorded_events(self.replay)
        return dict(self._artifact_recovery_report)

    def confirm_unit_sunk(self, *, event_id: str, timestamp_ns: int, unit_id: str, authoritative_unit_state) -> ReplayEvent:
        """Publish a server-confirmed sinking transition to the live replay log.

        Call only after the authoritative simulation has committed the unit's
        sunk state. Coordinates are read from that state, never from a client
        event payload. The method refuses afloat, mismatched, or incomplete units.
        """
        from collections.abc import Mapping
        from .provenance import EventProvenance

        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("unit_id must be a non-empty string")
        if not isinstance(timestamp_ns, int) or isinstance(timestamp_ns, bool) or timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if not isinstance(authoritative_unit_state, Mapping):
            raise ValueError("authoritative unit state is required")
        if str(authoritative_unit_state.get("id", "")) != unit_id:
            raise ValueError("sinking unit ID must match authoritative state")
        if authoritative_unit_state.get("unitType") != "submersible" or authoritative_unit_state.get("afloat") is not False:
            raise ValueError("only an authoritative sunk submersible can publish UNIT_SUNK")
        crew_id = authoritative_unit_state.get("crewId")
        if not isinstance(crew_id, str) or not crew_id.strip():
            raise ValueError("sunk submersible must have an authoritative crew ID")
        x, y = authoritative_unit_state.get("x"), authoritative_unit_state.get("y")
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("authoritative sinking coordinates must be numeric")
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("authoritative sinking coordinates must be numeric") from exc
        import math
        if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("authoritative sinking coordinates must be normalized finite values")
        event = ReplayEvent(
            event_id=event_id.strip(),
            timestamp_ns=timestamp_ns,
            kind="UNIT_SUNK",
            payload={
                "kind": "UNIT_SUNK",
                "status": "CONFIRMED",
                "event_id": event_id.strip(),
                "unit_id": unit_id.strip(),
                "crew_id": crew_id.strip(),
                "x": x,
                "y": y,
            },
            provenance=EventProvenance(
                source_type="simulation",
                source_ids=(unit_id.strip(),),
                timestamp_ns=timestamp_ns,
                confidence=1.0,
                metadata={"transition": "authoritative-unit-state"},
            ),
        )
        self.replay.append(event)
        return event

    def confirm_unit_removed(self, *, event_id: str, timestamp_ns: int, unit_id: str, authoritative_unit_state) -> ReplayEvent:
        """Publish confirmed carrier removal at its last authoritative position."""
        from collections.abc import Mapping
        import math

        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("unit_id must be a non-empty string")
        if not isinstance(timestamp_ns, int) or isinstance(timestamp_ns, bool) or timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if not isinstance(authoritative_unit_state, Mapping):
            raise ValueError("authoritative unit state is required")
        if str(authoritative_unit_state.get("id", "")) != unit_id:
            raise ValueError("removal unit ID must match authoritative state")
        if authoritative_unit_state.get("unitType") != "submersible":
            raise ValueError("only submersible removal can trigger artifact recovery")
        crew_id = authoritative_unit_state.get("crewId")
        if not isinstance(crew_id, str) or not crew_id.strip():
            raise ValueError("removed submersible must have an authoritative crew ID")
        x, y = authoritative_unit_state.get("x"), authoritative_unit_state.get("y")
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("authoritative removal coordinates must be numeric")
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("authoritative removal coordinates must be numeric") from exc
        if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("authoritative removal coordinates must be normalized finite values")
        event = ReplayEvent(
            event_id=event_id.strip(), timestamp_ns=timestamp_ns, kind="UNIT_REMOVED",
            payload={"kind": "UNIT_REMOVED", "status": "CONFIRMED",
                     "event_id": event_id.strip(), "unit_id": unit_id.strip(),
                     "crew_id": crew_id.strip(), "x": x, "y": y},
            provenance=EventProvenance(
                source_type="simulation", source_ids=(unit_id.strip(),),
                timestamp_ns=timestamp_ns, confidence=1.0,
                metadata={"transition": "authoritative-unit-removal"},
            ),
        )
        self.replay.append(event)
        return event
    def enable(self) -> None:
        self.enabled = True
        self.input.enable(True)
        if self.input_router is not None:
            self.input_router.vigil = self.input
            self.input_router.enable_vigil(True)

    def disable(self) -> None:
        self.enabled = False
        self.input.enable(False)
        if self.input_router is not None:
            self.input_router.enable_vigil(False)

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
        response = self.interaction.respond(
            request,
            analysis.text,
            grounded=bool(analysis.grounded_entity_ids),
            timestamp_ns=request.timestamp_ns,
            source_entity_ids=analysis.grounded_entity_ids,
            provenance=provenance,
        )
        self.replay.append(ReplayEvent(
            event_id=f"interaction-{request.request_id}",
            timestamp_ns=request.timestamp_ns,
            kind="interaction.response",
            payload=response,
            provenance=provenance,
        ))
        return response

    def _record_input_replay(self, event, interpretations) -> None:
        """Persist one Coreless input event and all VIGIL-derived interpretations."""
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

    def ingest_input_event(self, event) -> tuple[object, ...]:
        """Route a Coreless input event and persist its VIGIL interpretation chain."""
        if not self.enabled or self.input_router is None:
            return ()
        device = next((item for item in self.input_router.devices.devices if item.device_id == event.device_id), None)
        if device is None:
            raise ValueError("input event references an unknown Coreless device")
        interpretations = self.input_router.submit(event)
        self._record_input_replay(event, interpretations)
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
                interpretations = tuple(
                    item for item in self.input_router.interpreted_events
                    if item.source_sequence and item.source_sequence[-1] == touch_event.sequence
                )
                self._record_input_replay(touch_event, interpretations)
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

        self.replay.append(ReplayEvent(
            event_id=f"world-cycle-{frame.sequence}",
            timestamp_ns=frame.timestamp_ns,
            kind="world.state",
            payload=self.world.persistent_state(),
            provenance=EventProvenance(
                source_type="vigil.world",
                source_ids=(frame.source_id,),
                source_sequences=(frame.sequence,),
                timestamp_ns=frame.timestamp_ns,
            ),
        ))
        self.replay.append(ReplayEvent(
            event_id=f"priority-{frame.sequence}",
            timestamp_ns=frame.timestamp_ns,
            kind="vigil.priority",
            payload=ordered_priority,
            provenance=EventProvenance(
                source_type="vigil.priority",
                source_ids=(frame.source_id,),
                source_sequences=(frame.sequence,),
                timestamp_ns=frame.timestamp_ns,
            ),
        ))
        self.replay.append(ReplayEvent(
            event_id=f"attention-{frame.sequence}",
            timestamp_ns=frame.timestamp_ns,
            kind="vigil.attention",
            payload=attention_items,
            provenance=EventProvenance(
                source_type="vigil.attention",
                source_ids=(frame.source_id,),
                source_sequences=(frame.sequence,),
                timestamp_ns=frame.timestamp_ns,
            ),
        ))
        self.replay.append(ReplayEvent(
            event_id=f"presentation-{frame.sequence}",
            timestamp_ns=frame.timestamp_ns,
            kind="vigil.presentation",
            payload=presentation_state,
            provenance=EventProvenance(
                source_type="vigil.presentation",
                source_ids=(frame.source_id,),
                source_sequences=(frame.sequence,),
                timestamp_ns=frame.timestamp_ns,
            ),
        ))

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
            "fast_touch": self.fast_touch.persistent_state() if self.fast_touch is not None else None,
            "world": self.world.persistent_state(),
            "tracking": self.tracking.persistent_state(),
            "attention": self.attention.persistent_state(),
            "interaction": self.interaction.persistent_state(),
            "presentation": self.presentation.persistent_state(),
            "replay": self.replay.persistent_state(),
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", self.VERSION)) != self.VERSION:
            raise ValueError("unsupported VIGIL environment state version")
        self.enabled = bool(state.get("enabled", False))
        camera_state = state.get("camera")
        if self.camera is not None and isinstance(camera_state, Mapping):
            self.camera.restore_state(camera_state)
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
        presentation_state = state.get("presentation")
        if isinstance(presentation_state, Mapping):
            self.presentation.restore_state(presentation_state)
        fast_touch_state = state.get("fast_touch")
        if self.fast_touch is not None and isinstance(fast_touch_state, Mapping):
            self.fast_touch.restore_state(fast_touch_state)
        # restore_state replaces ReplayLog. Rebind the recovery consumer to the
        # restored log, then reconcile old lifecycle events before normal play.
        if self._artifact_recovery_consumer is not None:
            if self._artifact_recovery_unsubscribe is not None:
                self._artifact_recovery_unsubscribe()
            self._artifact_recovery_unsubscribe = self._artifact_recovery_consumer.attach(self.replay)
            self._artifact_recovery_report = self._artifact_recovery_consumer.reconcile_recorded_events(self.replay)
        self.input.enable(self.enabled)
        if self.input_router is not None:
            self.input_router.vigil = self.input
            self.input_router.enable_vigil(self.enabled)
