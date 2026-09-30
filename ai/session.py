"""Human-AI terminal/session control plane.

The session layer translates user input into AI requests and exposes structured
results. It never treats conversational text as authorization and never
executes AI proposals directly.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    def close(self) -> None:
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def events(self) -> tuple[SessionEvent, ...]:
        return tuple(self._events)
