"""AI-Core registry for 314DNest.

The registry is deliberately small: it manages model identities and lifecycle
without granting models privileged Coreless authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable, Mapping

from .interfaces import AICore, AIRequest, AIResult


@dataclass(frozen=True)
class AICoreDescriptor:
    model_id: str
    provider: str
    local: bool = True
    enabled: bool = True


class AICoreRegistry:
    STATE_VERSION = 1
    """Register, enable, disable, and invoke AI cores through one contract."""

    def __init__(self) -> None:
        self._cores: dict[str, AICore] = {}
        self._descriptors: dict[str, AICoreDescriptor] = {}

    def register(
        self,
        core: AICore,
        *,
        provider: str = "local",
        local: bool = True,
        enabled: bool = True,
    ) -> AICoreDescriptor:
        model_id = core.model_id
        if model_id in self._cores:
            raise ValueError(f"AI core already registered: {model_id}")
        descriptor = AICoreDescriptor(
            model_id=model_id,
            provider=provider,
            local=local,
            enabled=enabled,
        )
        self._cores[model_id] = core
        self._descriptors[model_id] = descriptor
        return descriptor

    def unregister(self, model_id: str) -> None:
        self._cores.pop(model_id)
        self._descriptors.pop(model_id)

    def set_enabled(self, model_id: str, enabled: bool) -> None:
        descriptor = self._require_descriptor(model_id)
        self._descriptors[model_id] = AICoreDescriptor(
            model_id=descriptor.model_id,
            provider=descriptor.provider,
            local=descriptor.local,
            enabled=enabled,
        )

    def descriptor(self, model_id: str) -> AICoreDescriptor:
        return self._require_descriptor(model_id)

    def descriptors(self) -> tuple[AICoreDescriptor, ...]:
        return tuple(self._descriptors.values())

    def enabled_cores(self) -> tuple[str, ...]:
        return tuple(
            model_id
            for model_id, descriptor in self._descriptors.items()
            if descriptor.enabled
        )

    def to_state(self) -> dict[str, object]:
        return {"version": self.STATE_VERSION, "cores": [
            {"model_id": d.model_id, "provider": d.provider, "local": d.local, "enabled": d.enabled}
            for d in self.descriptors()
        ]}

    def restore_state(self, state: Mapping[str, object]) -> None:
        if not isinstance(state, Mapping) or state.get("version") != self.STATE_VERSION:
            raise ValueError("unsupported AI registry state version")
        entries = state.get("cores", [])
        if not isinstance(entries, list):
            raise ValueError("AI registry state has invalid core list")
        seen = set()
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("AI registry state contains an invalid core")
            model_id = entry.get("model_id")
            if not isinstance(model_id, str) or model_id in seen:
                raise ValueError("AI registry state contains duplicate or invalid model ID")
            seen.add(model_id)
            d = self._require_descriptor(model_id)
            provider, local, enabled = entry.get("provider", d.provider), entry.get("local", d.local), entry.get("enabled", d.enabled)
            if not isinstance(provider, str) or not isinstance(local, bool) or not isinstance(enabled, bool):
                raise ValueError("AI registry state contains invalid descriptor fields")
            self._descriptors[model_id] = AICoreDescriptor(model_id, provider, local, enabled)

    def save(self, storage: object, key: str = "ai/registry") -> None:
        writer = getattr(storage, "put", None) or getattr(storage, "write", None)
        if not callable(writer):
            raise TypeError("storage does not provide a write operation")
        writer(key, json.dumps(self.to_state(), sort_keys=True, separators=(",", ":")).encode("utf-8"))

    def load(self, storage: object, key: str = "ai/registry") -> None:
        reader = getattr(storage, "get", None) or getattr(storage, "read", None)
        if not callable(reader):
            raise TypeError("storage does not provide a read operation")
        try:
            raw = reader(key)
        except KeyError:
            raise KeyError("AI registry state not found") from None
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        try:
            state = json.loads(bytes(raw).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("AI registry state is not valid JSON") from exc
        self.restore_state(state)

    def infer(self, request: AIRequest, model_ids: Iterable[str] | None = None) -> tuple[AIResult, ...]:
        selected = tuple(model_ids) if model_ids is not None else self.enabled_cores()
        return tuple(self._infer_one(model_id, request) for model_id in selected)

    def _infer_one(self, model_id: str, request: AIRequest) -> AIResult:
        descriptor = self._require_descriptor(model_id)
        if not descriptor.enabled:
            raise RuntimeError(f"AI core is disabled: {model_id}")
        return self._cores[model_id].infer(request)

    def _require_descriptor(self, model_id: str) -> AICoreDescriptor:
        try:
            return self._descriptors[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown AI core: {model_id}") from exc
