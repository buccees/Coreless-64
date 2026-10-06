"""Persistent local-AI runtime integrated with the Coreless machine.

The runtime owns AI session continuity, model registration, multi-core
coordination, and durable state. Model execution remains an ordinary compute
operation; AI output never becomes Coreless authorization by itself.
"""
from __future__ import annotations

from typing import Any, Mapping

from .coordinator import CoordinationResult, NestCoordinator
from .interfaces import AIResult, AuthorityLevel, GroupResult
from .local_runtime import register_default_local_cores
from .registry import AICoreRegistry
from .session import AISession, TerminalMessage


class PersistentAIRuntime:
    STATE_VERSION = 1
    SESSION_KEY = "ai/session/default"
    REGISTRY_KEY = "ai/registry"

    def __init__(
        self,
        storage: Any,
        *,
        session_id: str = "default",
        authority: AuthorityLevel = AuthorityLevel.RECOMMEND,
        local_cores: bool = True,
        endpoint: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.storage = storage
        self.registry = AICoreRegistry()
        if local_cores:
            register_default_local_cores(self.registry, endpoint=endpoint, timeout=timeout)
        self.session = AISession(session_id, authority=authority)
        self.coordinator = NestCoordinator(self.registry)

    def request(self, text: str, *, actor: str = "human"):
        return self.session.request(TerminalMessage(
            message_id=f"{self.session.session_id}:message:{self.session._counter + 1}",
            text=text,
            actor=actor,
        ))

    def analyze(
        self,
        text: str,
        *,
        actor: str = "human",
        context: Mapping[str, object] | None = None,
        model_ids: tuple[str, ...] | None = None,
    ) -> CoordinationResult:
        request = self.request(text, actor=actor)
        if context:
            request = type(request)(
                request_id=request.request_id,
                prompt=request.prompt,
                context={**request.context, **dict(context)},
                authority=request.authority,
            )
        result = self.coordinator.coordinate(request, model_ids)
        for item in result.results:
            self.session.record_result(item)
        self.session.record_group(result.group)
        self.save()
        return result

    def compute(
        self,
        machine: Any,
        text: str,
        *,
        model_id: str,
        actor: str = "human",
        context: Mapping[str, object] | None = None,
        operation: str = "ai.infer",
    ):
        """Execute one persistent AI request through the machine scheduler."""
        from .compute_fabric import ComputeWork

        request = self.request(text, actor=actor)
        if context:
            request = type(request)(
                request_id=request.request_id,
                prompt=request.prompt,
                context={**request.context, **dict(context)},
                authority=request.authority,
            )
        work = ComputeWork(
            work_id=f"{self.session.session_id}:work:{request.request_id.rsplit(':', 1)[-1]}",
            operation=operation,
            request=request,
        )
        result = machine.schedule_compute(work, preference="ai", allow_fallback=False)
        self.session.record_result(result[0].result)
        self.save()
        return result
    def save(self) -> None:
        self.registry.save(self.storage, self.REGISTRY_KEY)
        self.session.save(self.storage, self.SESSION_KEY)

    def restore(self) -> None:
        try:
            self.registry.load(self.storage, self.REGISTRY_KEY)
        except KeyError:
            pass
        try:
            self.session = AISession.load(
                self.storage, self.session.session_id, self.SESSION_KEY
            )
        except KeyError:
            pass

    def state(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "session": self.session.to_state(),
            "registry": self.registry.to_state(),
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if state.get("version") != self.STATE_VERSION:
            raise ValueError("unsupported persistent AI runtime state version")
        session_state = state.get("session")
        registry_state = state.get("registry")
        if not isinstance(session_state, Mapping) or not isinstance(registry_state, Mapping):
            raise ValueError("persistent AI runtime state is incomplete")
        self.session = AISession.from_state(session_state)
        self.registry.restore_state(registry_state)

    def status(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "session_id": self.session.session_id,
            "session_active": self.session.active,
            "authority": self.session.authority.value,
            "registered_cores": self.registry.descriptors(),
            "enabled_cores": self.registry.enabled_cores(),
            "event_count": len(self.session.events()),
        }
