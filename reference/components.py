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

    VERSION = 1
    COMPONENT_OBJECT_PREFIX = "machine/components/"

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

    def start_vm(self):
        """Start this component's bound Coreless VM."""
        if self.vm is None:
            raise RuntimeError("component has no Coreless VM")
        runner = getattr(self.vm, "run", None)
        if callable(runner):
            runner()
        elif hasattr(self.vm, "running"):
            self.vm.running = True
        else:
            raise TypeError("bound VM does not expose a Coreless lifecycle")
        return self.vm

    def stop_vm(self):
        """Stop this component's bound Coreless VM."""
        if self.vm is None:
            raise RuntimeError("component has no Coreless VM")
        stopper = getattr(self.vm, "stop", None)
        if callable(stopper):
            stopper()
        elif hasattr(self.vm, "running"):
            self.vm.running = False
        else:
            raise TypeError("bound VM does not expose a Coreless lifecycle")
        return self.vm

    def reset_vm(self):
        """Reset the bound VM's execution state without replacing its identity."""
        if self.vm is None:
            raise RuntimeError("component has no Coreless VM")
        self.stop_vm()
        if not hasattr(self.vm, "vcpus"):
            raise TypeError("bound VM does not expose Coreless vCPU state")
        for vcpu in self.vm.vcpus:
            vcpu.registers = [0] * 32
            vcpu.pc = 0
            vcpu.sp = 0
            vcpu.privilege = 0
            vcpu.halted = False
            vcpu.inbox.clear()
        pending = getattr(self.vm, "pending_interrupts", None)
        if pending is not None:
            pending.clear()
        return self.vm

    def vm_status(self) -> dict[str, object]:
        """Return the live lifecycle state of the bound Coreless VM."""
        if self.vm is None:
            return {"bound": False, "running": False}
        return {
            "bound": True,
            "vm_id": self.descriptor.vm_id,
            "running": bool(getattr(self.vm, "running", False)),
            "vcpus": len(getattr(self.vm, "vcpus", ())),
        }


    def start_ai(self):
        """Start this component's local AI runtime."""
        if self.ai_runtime is None:
            raise RuntimeError("component has no Coreless AI runtime")
        starter = getattr(self.ai_runtime, "start", None)
        if callable(starter):
            starter()
        elif hasattr(self.ai_runtime, "running"):
            self.ai_runtime.running = True
        else:
            raise TypeError("bound AI runtime does not expose a Coreless lifecycle")
        return self.ai_runtime

    def stop_ai(self):
        """Stop this component's local AI runtime."""
        if self.ai_runtime is None:
            raise RuntimeError("component has no Coreless AI runtime")
        stopper = getattr(self.ai_runtime, "stop", None)
        if callable(stopper):
            stopper()
        elif hasattr(self.ai_runtime, "running"):
            self.ai_runtime.running = False
        else:
            raise TypeError("bound AI runtime does not expose a Coreless lifecycle")
        return self.ai_runtime

    def ai_status(self) -> dict[str, object]:
        """Return the live state and specialization of the local AI runtime."""
        if self.ai_runtime is None:
            return {
                "bound": False,
                "running": False,
                "model_id": self.descriptor.ai_model_id,
                "role": self.descriptor.role,
            }
        return {
            "bound": True,
            "running": bool(getattr(self.ai_runtime, "running", False)),
            "model_id": self.descriptor.ai_model_id,
            "role": self.descriptor.role,
        }

    def require_ai_vm(self) -> None:
        """Require both local AI and VM boundaries for model adaptation work."""
        if self.ai_runtime is None:
            raise RuntimeError("component has no Coreless AI runtime")
        if self.vm is None:
            raise RuntimeError("component has no Coreless VM")

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

    def __init__(self, hub_id: str = "coreless-hub-0", *, hypervisor: object | None = None) -> None:
        if not hub_id:
            raise ValueError("hub_id must not be empty")
        self.hub_id = hub_id
        self.hypervisor = hypervisor
        self._components: dict[str, CorelessComponent] = {}
        self._ipc_channels: dict[tuple[str, str], int] = {}

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

    def negotiate(self, source_id: str, target_id: str, required: frozenset[str] | set[str] = frozenset()) -> frozenset[str]:
        """Negotiate a capability set between two connected components."""
        source = self.component(source_id)
        target = self.component(target_id)
        required = frozenset(required)
        shared = source.descriptor.capabilities & target.descriptor.capabilities
        if not required.issubset(shared):
            missing = sorted(required - shared)
            raise ValueError(f"capability negotiation failed: {missing}")
        return frozenset(shared)

    def open_ipc(self, source_id: str, target_id: str, required: frozenset[str] | set[str] = frozenset()) -> int:
        """Authorize a VM-to-VM IPC channel after capability negotiation."""
        self.negotiate(source_id, target_id, required)
        if self.hypervisor is None:
            raise RuntimeError("hub has no Coreless Hypervisor")
        source = self.component(source_id)
        target = self.component(target_id)
        if source.vm is None or target.vm is None:
            raise RuntimeError("both components require bound VMs for IPC")
        source_vmid = int(source.vm.vmid)
        target_vmid = int(target.vm.vmid)
        capability = self.hypervisor.grant_ipc(source_vmid, target_vmid)
        self._ipc_channels[(source_id, target_id)] = capability
        return capability

    def close_ipc(self, source_id: str, target_id: str) -> None:
        """Revoke a previously negotiated VM-to-VM IPC channel."""
        capability = self._ipc_channels.pop((source_id, target_id), None)
        if capability is not None and self.hypervisor is not None:
            self.hypervisor.revoke_ipc(capability)

    def send_ipc(self, source_id: str, target_id: str, payload: bytes, *, source_vcpu: int = 0, target_vcpu: int = 0) -> None:
        """Send data through an authorized hub IPC channel."""
        if self.hypervisor is None:
            raise RuntimeError("hub has no Coreless Hypervisor")
        capability = self._ipc_channels.get((source_id, target_id))
        if capability is None:
            raise PermissionError("IPC channel has not been negotiated")
        source = self.component(source_id)
        target = self.component(target_id)
        self.hypervisor.send_message(
            int(source.vm.vmid), source_vcpu, int(target.vm.vmid), target_vcpu,
            payload, capability=capability,
        )

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
