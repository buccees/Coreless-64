"""Human interaction boundary for Coreless-native VIGIL."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from .provenance import EventProvenance


class InputModality(str, Enum):
    TEXT = "text"
    VOICE = "voice"


@dataclass(frozen=True)
class InteractionRequest:
    request_id: str
    modality: InputModality
    text: str
    timestamp_ns: int
    session_id: str
    authorization_scope: str
    metadata: Mapping[str, object] = None
    provenance: EventProvenance | None = None

    def __post_init__(self) -> None:
        if not self.request_id or not self.session_id:
            raise ValueError("request_id and session_id must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")


@dataclass(frozen=True)
class InteractionResponse:
    request_id: str
    text: str
    grounded: bool
    timestamp_ns: int
    source_entity_ids: tuple[str, ...] = ()
    metadata: Mapping[str, object] = None
    provenance: EventProvenance | None = None


class VoiceInputSource(Protocol):
    """Optional Coreless-owned voice transport/transcription boundary."""
    def available(self) -> bool:
        ...
    def read(self) -> tuple[str, int] | None:
        ...


@dataclass(frozen=True)
class VoiceInput:
    text: str
    timestamp_ns: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("voice input text must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("voice input timestamp_ns must be non-negative")


class HumanInteractionService:
    def __init__(self) -> None:
        self._context: list[str] = []

    def remember(self, text: str) -> None:
        if text:
            self._context.append(text)

    def respond(self, request: InteractionRequest, answer: str, *, grounded: bool, timestamp_ns: int, source_entity_ids: tuple[str, ...] = (), provenance: EventProvenance | None = None) -> InteractionResponse:
        self.remember(request.text)
        self.remember(answer)
        return InteractionResponse(request.request_id, answer, grounded, timestamp_ns, source_entity_ids, provenance=provenance)

    def persistent_state(self) -> dict[str, object]:
        return {"version": 1, "context": list(self._context)}

    def restore_state(self, state: object) -> None:
        if not isinstance(state, Mapping) or state.get("version") != 1:
            raise ValueError("unsupported interaction state version")
        context = state.get("context", [])
        if not isinstance(context, list) or not all(isinstance(item, str) for item in context):
            raise ValueError("interaction context must be a list of strings")
        self._context = list(context)
