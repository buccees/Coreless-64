"""Human-AI terminal/session control plane.

The session layer translates user input into AI requests and exposes structured
results. It never treats conversational text as authorization and never
executes AI proposals directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from .interfaces import AIRequest, AIResult, AuthorityLevel, GroupResult


@dataclass(frozen=True)
class TerminalMessage:
    message_id: str
    text: str
    actor: str = "human"


@dataclass(frozen=True)
class SessionEvent:
    event_id: str
    kind: str
    payload: Mapping[str, object]


class AISession:
    STATE_VERSION = 1

    def __init__(self, session_id: str, *, authority: AuthorityLevel = AuthorityLevel.RECOMMEND) -> None:
        self.session_id = session_id
        self.authority = authority
        self._events: list[SessionEvent] = []
        self._counter = 0
        self._active = True

    def request(self, message: TerminalMessage) -> AIRequest:
        if not self._active:
            raise RuntimeError("session is closed")
        self._counter += 1
        request_id = f"{self.session_id}:request:{self._counter}"
        request = AIRequest(
            request_id=request_id,
            prompt=message.text,
            context={"session_id": self.session_id, "actor": message.actor},
            authority=self.authority,
        )
        self._events.append(SessionEvent(
            f"{self.session_id}:event:{self._counter}",
            "request",
            {"request_id": request_id, "actor": message.actor},
        ))
        return request

    def record_result(self, result: AIResult) -> None:
        self._events.append(SessionEvent(
            f"{self.session_id}:event:{self._counter + 1}",
            "result",
            {"request_id": result.request_id, "model_id": result.model_id, "text": result.text},
        ))
        self._counter += 1

    def record_group(self, group: GroupResult) -> None:
        self._events.append(SessionEvent(
            f"{self.session_id}:event:{self._counter + 1}",
            "group_result",
            {
                "request_id": group.request_id,
                "participants": tuple(group.participants),
                "authorization_required": group.authorization_required,
            },
        ))
        self._counter += 1

    def to_state(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "session_id": self.session_id,
            "authority": self.authority.value,
            "counter": self._counter,
            "active": self._active,
            "events": [{"event_id": e.event_id, "kind": e.kind, "payload": dict(e.payload)} for e in self._events],
        }

    @classmethod
    def from_state(cls, state: Mapping[str, object]) -> "AISession":
        if not isinstance(state, Mapping) or state.get("version") != cls.STATE_VERSION:
            raise ValueError("unsupported AI session state version")
        session_id = state.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("AI session state has invalid session ID")
        try:
            authority = AuthorityLevel(state.get("authority", AuthorityLevel.RECOMMEND.value))
        except ValueError as exc:
            raise ValueError("AI session state has invalid authority") from exc
        counter, active, events = state.get("counter", 0), state.get("active", True), state.get("events", [])
        if not isinstance(counter, int) or counter < 0 or not isinstance(active, bool) or not isinstance(events, list):
            raise ValueError("AI session state has invalid lifecycle fields")
        session = cls(session_id, authority=authority)
        restored = []
        for item in events:
            if not isinstance(item, Mapping):
                raise ValueError("AI session state contains an invalid event")
            event_id, kind, payload = item.get("event_id"), item.get("kind"), item.get("payload", {})
            if not isinstance(event_id, str) or not isinstance(kind, str) or not isinstance(payload, Mapping):
                raise ValueError("AI session state contains malformed event fields")
            restored.append(SessionEvent(event_id, kind, dict(payload)))
        session._events, session._counter, session._active = restored, counter, active
        return session

    def save(self, storage: object, key: str | None = None) -> None:
        storage_key = key or f"ai/session/{self.session_id}"
        writer = getattr(storage, "put", None) or getattr(storage, "write", None)
        if not callable(writer):
            raise TypeError("storage does not provide a write operation")
        writer(storage_key, json.dumps(self.to_state(), sort_keys=True, separators=(",", ":")).encode("utf-8"))

    @classmethod
    def load(cls, storage: object, session_id: str, key: str | None = None) -> "AISession":
        storage_key = key or f"ai/session/{session_id}"
        reader = getattr(storage, "get", None) or getattr(storage, "read", None)
        if not callable(reader):
            raise TypeError("storage does not provide a read operation")
        try:
            raw = reader(storage_key)
        except KeyError:
            raise KeyError(f"AI session not found: {session_id}") from None
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        try:
            state = json.loads(bytes(raw).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("AI session state is not valid JSON") from exc
        session = cls.from_state(state)
        if session.session_id != session_id:
            raise ValueError("AI session ID does not match storage key")
        return session

    def close(self) -> None:
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def events(self) -> tuple[SessionEvent, ...]:
        return tuple(self._events)
