"""Autonomous and composable Coreless component model.

A component is a complete Coreless machine boundary that can operate alone,
carry its own AI/VM identity, specialize around a role, and join a Coreless
Hub without becoming a passive peripheral.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ComponentDescriptor:
    """Identity and specialization contract for one Coreless component."""

    component_id: str
    role: str
    capabilities: frozenset[str]
    ai_model_id: str | None = None
    vm_id: str | None = None
    version: int = 1

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "role": self.role,
            "capabilities": sorted(self.capabilities),
            "ai_model_id": self.ai_model_id,
            "vm_id": self.vm_id,
            "version": self.version,
        }


class CorelessComponent:
    """A complete Coreless unit that can run independently or compose."""

    def __init__(
        self,
        descriptor: ComponentDescriptor,
        *,
        system: object | None = None,
        ai_runtime: object | None = None,
        vm: object | None = None,
    ) -> None:
        if not descriptor.component_id:
            raise ValueError("component_id must not be empty")
        if not descriptor.role:
            raise ValueError("role must not be empty")
        self.descriptor = descriptor
        self.system = system
        self.ai_runtime = ai_runtime
        self.vm = vm
        self._hub_id: str | None = None

    @property
    def component_id(self) -> str:
        return self.descriptor.component_id

    @property
    def standalone(self) -> bool:
        return self._hub_id is None

    @property
    def hub_id(self) -> str | None:
        return self._hub_id

    def attach(self, hub_id: str) -> None:
        if not hub_id:
            raise ValueError("hub_id must not be empty")
        if self._hub_id is not None and self._hub_id != hub_id:
            raise ValueError(
                f"component already attached to hub: {self._hub_id}"
            )
        self._hub_id = hub_id

    def detach(self, hub_id: str) -> None:
        if self._hub_id != hub_id:
            raise ValueError("component is not attached to this hub")
        self._hub_id = None

    @property
    def persistence_key(self) -> str:
        return f"{self.COMPONENT_OBJECT_PREFIX}{self.component_id}"

    def persist_identity(self) -> None:
        """Persist identity and specialization in the component machine image."""
        if self.system is None:
            raise RuntimeError("component has no CorelessSystem")
        payload = {
            "version": self.VERSION,
            "descriptor": self.descriptor.to_dict(),
        }
        self.system.machine.storage.put(
            self.persistence_key,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            sync=False,
        )

    def restore_identity(self) -> ComponentDescriptor:
        """Restore and validate this component's persisted identity."""
        if self.system is None:
            raise RuntimeError("component has no CorelessSystem")
        raw = self.system.machine.storage.objects.get(self.persistence_key)
        if raw is None:
            raise KeyError(f"no persisted identity: {self.component_id}")
        payload = json.loads(raw.decode("utf-8"))
        if payload.get("version") != self.VERSION:
            raise ValueError("unsupported Coreless component manifest version")
        descriptor = payload.get("descriptor")
        if not isinstance(descriptor, dict):
            raise ValueError("invalid Coreless component descriptor")
        if descriptor.get("component_id") != self.component_id:
            raise ValueError("persisted component identity mismatch")
        return ComponentDescriptor(
            component_id=descriptor["component_id"],
            role=descriptor["role"],
            capabilities=frozenset(descriptor["capabilities"]),
            ai_model_id=descriptor.get("ai_model_id"),
            vm_id=descriptor.get("vm_id"),
            version=descriptor["version"],
        )

    def boot(self):
        if self.system is None:
            raise RuntimeError("component has no CorelessSystem")
        self.persist_identity()
        self.system.boot()
        return self

    def shutdown(self):
        if self.system is None:
            return None
        return self.system.shutdown()

    def status(self) -> dict[str, object]:
        return {
            "component": self.descriptor.to_dict(),
            "standalone": self.standalone,
            "hub_id": self.hub_id,
            "system_integrated": self.system is not None,
            "ai_integrated": self.ai_runtime is not None
            or self.descriptor.ai_model_id is not None,
            "vm_integrated": self.vm is not None
            or self.descriptor.vm_id is not None,
        }


class CorelessHub:
    """Discovery and composition boundary for autonomous Coreless components."""

    VERSION = 1
    COMPONENT_OBJECT_PREFIX = "machine/components/"

    def __init__(self, hub_id: str = "coreless-hub-0") -> None:
        if not hub_id:
            raise ValueError("hub_id must not be empty")
        self.hub_id = hub_id
        self._components: dict[str, CorelessComponent] = {}

    def connect(self, component: CorelessComponent) -> ComponentDescriptor:
        existing = self._components.get(component.component_id)
        if existing is not None and existing is not component:
            raise ValueError(
                f"component already registered: {component.component_id}"
            )
        component.attach(self.hub_id)
        self._components[component.component_id] = component
        return component.descriptor

    def disconnect(self, component_id: str) -> CorelessComponent:
        try:
            component = self._components.pop(component_id)
        except KeyError as exc:
            raise KeyError(f"unknown component: {component_id}") from exc
        component.detach(self.hub_id)
        return component

    def component(self, component_id: str) -> CorelessComponent:
        try:
            return self._components[component_id]
        except KeyError as exc:
            raise KeyError(f"unknown component: {component_id}") from exc

    def components(self) -> tuple[CorelessComponent, ...]:
        return tuple(self._components.values())

    def discover(self) -> tuple[ComponentDescriptor, ...]:
        return tuple(component.descriptor for component in self.components())

    def capabilities(self) -> frozenset[str]:
        capabilities: set[str] = set()
        for component in self.components():
            capabilities.update(component.descriptor.capabilities)
        return frozenset(capabilities)

    def composition(self) -> Mapping[str, object]:
        return {
            "hub_id": self.hub_id,
            "version": self.VERSION,
            "component_count": len(self._components),
            "components": tuple(
                component.descriptor.to_dict() for component in self.components()
            ),
            "capabilities": tuple(sorted(self.capabilities())),
            "unified": bool(self._components),
        }
