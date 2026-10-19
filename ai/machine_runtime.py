"""Persistent local-AI runtime integrated with the Coreless machine.

The runtime owns AI session continuity, model registration, multi-core
coordination, and durable state. Model execution remains an ordinary compute
operation; AI output never becomes Coreless authorization by itself.
"""
from __future__ import annotations

from typing import Any, Mapping

from .coordinator import CoordinationResult, NestCoordinator
from .interfaces import AIResult, AuthorityLevel, GroupResult
from .function_router import FunctionalModelRouter
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
        self.function_router = FunctionalModelRouter(self.registry)

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

    def declare_model_functions(self, model_id: str, functions: tuple[str, ...]) -> None:
        """Record functions validated for a model; names are never used as evidence."""
        self.function_router.declare_capabilities(model_id, functions)
        self.function_router.save(self.storage)

    def assign_function(self, function: str, model_id: str) -> None:
        """Assign a model only after its function capability has been declared."""
        self.function_router.assign(function, model_id)
        self.function_router.save(self.storage)

    def analyze_for_function(
        self,
        function: str,
        text: str,
        *,
        actor: str = "human",
        context: Mapping[str, object] | None = None,
    ) -> CoordinationResult:
        """Run analysis only on enabled models assigned to the requested function."""
        model_ids = self.function_router.models_for(function)
        return self.analyze(text, actor=actor, context=context, model_ids=model_ids)

    def compute_for_function(
        self,
        machine: Any,
        function: str,
        text: str,
        *,
        actor: str = "human",
        context: Mapping[str, object] | None = None,
        operation: str = "ai.infer",
    ):
        """Execute assigned models through the machine's digital AI chipset and scheduler.

        Models run in declared assignment order. No conventional-CPU fallback or
        unassigned model substitution is permitted.
        """
        from .compute_fabric import ComputeWork

        model_ids = self.function_router.models_for(function)
        chipset = getattr(machine, "ai_chipset", None)
        dispatch = getattr(chipset, "dispatch", None)
        if not callable(dispatch):
            raise TypeError("machine does not expose the digital AI chipset dispatch contract")

        request = self.request(text, actor=actor)
        if context:
            request = type(request)(
                request_id=request.request_id,
                prompt=request.prompt,
                context={**request.context, **dict(context)},
                authority=request.authority,
            )
        request_number = request.request_id.rsplit(":", 1)[-1]
        results = []
        for index, model_id in enumerate(model_ids):
            work = ComputeWork(
                work_id=f"{self.session.session_id}:function:{function}:{request_number}:{index}",
                operation=operation,
                request=request,
                model_id=model_id,
            )
            result = dispatch(work, model_id=model_id)
            ai_result = getattr(result, "result", None)
            if ai_result is None or getattr(ai_result, "model_id", None) != model_id:
                raise RuntimeError(
                    f"AI chipset returned invalid result provenance for function {function!r}"
                )
            self.session.record_result(ai_result)
            results.append(result)
        self.save()
        return tuple(results)

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
            model_id=model_id,
        )
        result = machine.schedule_compute(work, preference="ai", allow_fallback=False)
        self.session.record_result(result[0].result)
        self.save()
        return result
    def save(self) -> None:
        self.registry.save(self.storage, self.REGISTRY_KEY)
        self.session.save(self.storage, self.SESSION_KEY)
        self.function_router.save(self.storage)

    def restore(self) -> None:
        try:
            self.registry.load(self.storage, self.REGISTRY_KEY)
        except KeyError:
            pass
        try:
            self.function_router.load(self.storage)
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
            "function_router": self.function_router.to_state(),
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
        routing_state = state.get("function_router")
        if routing_state is not None:
            if not isinstance(routing_state, Mapping):
                raise ValueError("persistent AI runtime function routing is invalid")
            self.function_router.restore_state(routing_state)

    def status(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "session_id": self.session.session_id,
            "session_active": self.session.active,
            "authority": self.session.authority.value,
            "registered_cores": self.registry.descriptors(),
            "enabled_cores": self.registry.enabled_cores(),
            "function_assignments": self.function_router.assignments(),
            "event_count": len(self.session.events()),
        }
