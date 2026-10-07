"""Autonomous and composable Coreless component model.

A component is a complete Coreless machine boundary that can operate alone,
carry its own AI/VM identity, specialize around a role, and join a Coreless
Hub without becoming a passive peripheral.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Mapping
import threading


@dataclass(frozen=True)
class ComponentDescriptor:
    """Identity and specialization contract for one Coreless component."""

    component_id: str
    role: str
    capabilities: frozenset[str]
    ai_model_id: str | None = None
    vm_id: str | None = None
    version: int = 1
    capacity: int = 1

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
            "capacity": self.capacity,
        }


@dataclass(frozen=True)
class Workload:
    """A deterministic unit of work dispatched to a specialized component."""

    workload_id: str
    capability: str
    payload: object


@dataclass(frozen=True)
class WorkloadResult:
    """Result returned by the component that executed a workload."""

    workload_id: str
    component_id: str
    result: object

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
        workload_executor: Callable[[object], object] | None = None,
    ) -> None:
        if not descriptor.component_id:
            raise ValueError("component_id must not be empty")
        if not descriptor.role:
            raise ValueError("role must not be empty")
        if descriptor.capacity < 1:
            raise ValueError("component capacity must be positive")
        self.descriptor = descriptor
        self.system = system
        self.ai_runtime = ai_runtime
        self.vm = vm
        self.workload_executor = workload_executor
        self._hub_id: str | None = None
        self._healthy = True
        self._fault: str | None = None

    @property
    def component_id(self) -> str:
        return self.descriptor.component_id

    @property
    def standalone(self) -> bool:
        return self._hub_id is None

    @property
    def hub_id(self) -> str | None:
        return self._hub_id

    @property
    def healthy(self) -> bool:
        return self._healthy

    @property
    def fault(self) -> str | None:
        return self._fault

    def isolate(self, reason: str) -> None:
        """Place this component in a fault-isolated state without losing identity."""
        if not reason:
            raise ValueError("fault reason must not be empty")
        self._healthy = False
        self._fault = reason
        if self.vm is not None:
            try:
                self.stop_vm()
            except (RuntimeError, TypeError):
                pass
        if self.ai_runtime is not None:
            try:
                self.stop_ai()
            except (RuntimeError, TypeError):
                pass

    def recover(self) -> None:
        """Clear fault isolation while preserving component identity and bindings."""
        self._healthy = True
        self._fault = None

    def attach(self, hub_id: str) -> None:
        if not self._healthy:
            raise RuntimeError("faulted component must recover before hub attach")
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
        storage = getattr(self.system.machine, "storage", None)
        if storage is None:
            return
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
            capacity=descriptor.get("capacity", 1),
        )

    def boot(self, init_path: str = "/init"):
        if self.system is None:
            raise RuntimeError("component has no CorelessSystem")
        self.persist_identity()
        if init_path == "/init":
            try:
                self.system.boot()
            except TypeError:
                self.system.boot(init_path)
        else:
            self.system.boot(init_path)
        return self

    def resume(self, init_path: str | None = None):
        """Resume this component's persistent Coreless system."""
        if self.system is None:
            raise RuntimeError("component has no CorelessSystem")
        self.persist_identity()
        manifest = getattr(self.system, "boot_manifest", None)
        path = init_path or str((manifest or {}).get("init", "/init"))
        self.system.boot(path)
        return self

    def start_services(self) -> None:
        """Start the component-local VM and AI services when they are bound."""
        if self.vm is not None:
            self.start_vm()
        if self.ai_runtime is not None:
            try:
                self.start_ai()
            except (RuntimeError, TypeError):
                pass

    def stop_services(self) -> None:
        """Stop component-local AI and VM services without destroying identity."""
        if self.ai_runtime is not None:
            try:
                self.stop_ai()
            except (RuntimeError, TypeError):
                pass
        if self.vm is not None:
            try:
                self.stop_vm()
            except (RuntimeError, TypeError):
                pass

    def shutdown(self):
        self.stop_services()
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


    def execute_vm_steps(self, hypervisor: object, count: int = 1, vcpu_id: int = 0) -> int:
        """Execute this component's bound VM through the native CPU boundary."""
        if not self.healthy:
            raise RuntimeError("cannot execute workload on fault-isolated component")
        if self.vm is None:
            raise RuntimeError("component has no Coreless VM")
        vmid = getattr(self.vm, "vmid", None)
        if vmid is None:
            raise TypeError("bound VM has no vmid")
        if getattr(hypervisor, "bound_cpu")(vmid, vcpu_id) is None:
            raise RuntimeError("component VM vCPU has no bound native CPU")
        return hypervisor.step(vmid, count=count, vcpu_id=vcpu_id)

    def execute_hub_vm_steps(self, hub: "CorelessHub", count: int = 1, vcpu_id: int = 0) -> int:
        """Execute this component VM through the Hub-owned native execution boundary."""
        if not self.healthy:
            raise RuntimeError("cannot execute workload on fault-isolated component")
        if self._hub_id != hub.hub_id:
            raise RuntimeError("component is not attached to this Coreless Hub")
        return hub.execute_component_vm(self.component_id, count=count, vcpu_id=vcpu_id)

    def execute_hub_workload(self, hub: "CorelessHub", workload: Workload) -> WorkloadResult:
        """Execute a workload through this component's unified Hub boundary."""
        if not self.healthy:
            raise RuntimeError("cannot execute workload on fault-isolated component")
        if self._hub_id != hub.hub_id:
            raise RuntimeError("component is not attached to this Coreless Hub")
        return hub.dispatch(workload)

    def execute_workload(self, workload: Workload) -> WorkloadResult:
        """Execute one workload inside this component's local boundary."""
        if not self.healthy:
            raise RuntimeError("cannot execute workload on fault-isolated component")
        if not self.descriptor.supports(workload.capability):
            raise ValueError(
                f"component does not support workload capability: {workload.capability}"
            )
        if self.workload_executor is None:
            raise RuntimeError("component has no workload executor")
        return WorkloadResult(
            workload.workload_id,
            self.component_id,
            self.workload_executor(workload.payload),
        )

    def status(self) -> dict[str, object]:
        return {
            "component": self.descriptor.to_dict(),
            "standalone": self.standalone,
            "hub_id": self.hub_id,
            "healthy": self.healthy,
            "fault": self.fault,
            "system_integrated": self.system is not None,
            "ai_integrated": self.ai_runtime is not None
            or self.descriptor.ai_model_id is not None,
            "vm_integrated": self.vm is not None
            or self.descriptor.vm_id is not None,
            "capacity": self.descriptor.capacity,
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
        self._dispatch_load: dict[str, int] = {}
        self._dispatch_condition = threading.Condition()

    def connect(self, component: CorelessComponent) -> ComponentDescriptor:
        if not component.healthy:
            raise RuntimeError("cannot connect a fault-isolated component")
        existing = self._components.get(component.component_id)
        if existing is not None and existing is not component:
            raise ValueError(
                f"component already registered: {component.component_id}"
            )
        component.attach(self.hub_id)
        self._components[component.component_id] = component
        with self._dispatch_condition:
            self._dispatch_load.setdefault(component.component_id, 0)
            self._dispatch_condition.notify_all()
        return component.descriptor

    def disconnect(self, component_id: str) -> CorelessComponent:
        try:
            component = self._components.pop(component_id)
        except KeyError as exc:
            raise KeyError(f"unknown component: {component_id}") from exc
        component.detach(self.hub_id)
        for pair in tuple(self._ipc_channels):
            if component_id in pair:
                self.close_ipc(*pair)
        with self._dispatch_condition:
            self._dispatch_load.pop(component_id, None)
            self._dispatch_condition.notify_all()
        return component

    def isolate(self, component_id: str, reason: str) -> CorelessComponent:
        """Fault-isolate a connected component and revoke its hub channels."""
        component = self.component(component_id)
        for pair in tuple(self._ipc_channels):
            if component_id in pair:
                self.close_ipc(*pair)
        component.isolate(reason)
        component.detach(self.hub_id)
        self._components.pop(component_id, None)
        with self._dispatch_condition:
            self._dispatch_load.pop(component_id, None)
            self._dispatch_condition.notify_all()
        return component

    def rejoin(self, component: CorelessComponent) -> ComponentDescriptor:
        """Rejoin a recovered component after hot-plug or fault isolation."""
        component.recover()
        return self.connect(component)

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
        if not source.healthy or not target.healthy:
            raise RuntimeError("IPC requires healthy components")
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


    def boot(self, init_path: str = "/init") -> tuple[str, ...]:
        """Boot all connected systems as one composed Coreless computer.

        Components without a bound CorelessSystem remain autonomous and are
        simply left untouched.
        """
        started: list[CorelessComponent] = []
        try:
            for component in self.components():
                if not component.healthy:
                    continue
                if component.system is not None:
                    component.boot(init_path)
                component.start_services()
                if component.system is not None:
                    started.append(component)
        except Exception:
            for component in reversed(started):
                try:
                    component.shutdown()
                except (RuntimeError, TypeError):
                    pass
            raise
        return tuple(component.component_id for component in started)

    def resume(self) -> tuple[str, ...]:
        """Resume all connected persistent Coreless systems."""
        resumed: list[CorelessComponent] = []
        try:
            for component in self.components():
                if not component.healthy:
                    continue
                if component.system is not None:
                    component.resume()
                component.start_services()
                if component.system is not None:
                    resumed.append(component)
        except Exception:
            for component in reversed(resumed):
                try:
                    component.shutdown()
                except (RuntimeError, TypeError):
                    pass
            raise
        return tuple(component.component_id for component in resumed)

    def shutdown(self) -> tuple[str, ...]:
        """Shut down all connected systems while preserving the composition."""
        stopped: list[str] = []
        for component in reversed(self.components()):
            if component.system is not None:
                component.shutdown()
            elif component.vm is not None or component.ai_runtime is not None:
                component.stop_services()
                continue
            else:
                continue
            stopped.append(component.component_id)
        return tuple(stopped)

    def lifecycle_status(self) -> Mapping[str, object]:
        """Report unified lifecycle state without collapsing component identity."""
        return {
            "hub_id": self.hub_id,
            "booted_components": tuple(
                component.component_id
                for component in self.components()
                if component.system is not None
                and bool(getattr(component.system.machine, "booted", False))
            ),
            "component_count": len(self._components),
        }

    def checkpoint(self, name: str = "hub") -> Mapping[str, object]:
        """Checkpoint every persistent component as one composed machine."""
        targets = [
            component for component in self.components()
            if component.healthy and component.system is not None
        ]
        checkpoint_names = {
            component.component_id: f"{name}-{component.component_id}"
            for component in targets
        }
        manifest = {
            "version": self.VERSION,
            "hub_id": self.hub_id,
            "components": tuple(component.component_id for component in self.components()),
            "checkpoints": checkpoint_names,
        }
        results: dict[str, object] = {}
        # A coordinated checkpoint requires every persistent component to
        # have a writable storage object before any machine state is captured.
        # This prevents a successful snapshot from being published without a
        # Hub commit record on one of the participating components.
        checkpoint_key = f"machine/hub/{self.hub_id}/checkpoint"
        for component in targets:
            storage = getattr(component.system.machine, "storage", None)
            if storage is None or not hasattr(storage, "put"):
                raise RuntimeError(
                    f"component has no writable persistent storage: "
                    f"{component.component_id}"
                )

        # Snapshot all component systems first.  The Hub manifest is the
        # commit record: publish it only after every component checkpoint
        # succeeds so a partial checkpoint cannot appear coordinated.
        for component in targets:
            component.persist_identity()
            results[component.component_id] = component.system.checkpoint(
                checkpoint_names[component.component_id]
            )

        manifest_bytes = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        previous_manifests = {
            component.component_id: component.system.machine.storage.objects.get(checkpoint_key)
            for component in targets
        }

        try:
            for component in targets:
                storage = component.system.machine.storage
                storage.put(checkpoint_key, manifest_bytes, sync=False)
                sync = getattr(storage, "sync", None)
                if callable(sync):
                    sync()

            for component in targets:
                storage = component.system.machine.storage
                if storage.objects.get(checkpoint_key) != manifest_bytes:
                    raise RuntimeError(
                        "Coreless Hub checkpoint commit verification failed: "
                        f"{component.component_id}"
                    )

            for component in targets:
                checkpoint_name = checkpoint_names[component.component_id]
                storage = component.system.machine.storage
                listed = getattr(storage, "list_checkpoints", None)
                if callable(listed) and checkpoint_name not in listed():
                    raise RuntimeError(
                        "Coreless Hub checkpoint commit verification failed: "
                        f"missing checkpoint {checkpoint_name}"
                    )

            for component in targets:
                storage = component.system.machine.storage
                if storage.objects.get(checkpoint_key) != manifest_bytes:
                    raise RuntimeError(
                        "Coreless Hub checkpoint commit verification failed: "
                        f"manifest changed after commit: {component.component_id}"
                    )
                sync = getattr(storage, "sync", None)
                if callable(sync):
                    sync()

            for component in targets:
                storage = component.system.machine.storage
                if storage.objects.get(checkpoint_key) != manifest_bytes:
                    raise RuntimeError(
                        "Coreless Hub checkpoint commit verification failed: "
                        f"manifest changed after durability sync: {component.component_id}"
                    )
        except Exception:
            # Restore the prior commit record everywhere if publication or
            # verification fails, preventing a partially committed manifest.
            for component in targets:
                storage = component.system.machine.storage
                previous = previous_manifests[component.component_id]
                if previous is None:
                    storage.objects.pop(checkpoint_key, None)
                else:
                    storage.objects[checkpoint_key] = previous
                sync = getattr(storage, "sync", None)
                if callable(sync):
                    sync()
            raise

        return {
            "hub_id": self.hub_id,
            "checkpoints": results,
            "committed": True,
            "manifest_version": self.VERSION,
            "component_count": len(targets),
        }

    def restore(self, name: str = "hub") -> tuple[str, ...]:
        """Restore every persistent component from a coordinated Hub checkpoint."""
        targets = [
            component for component in self.components()
            if component.healthy and component.system is not None
        ]
        expected = tuple(component.component_id for component in self.components())
        expected_checkpoints = {component.component_id for component in targets}
        plans: list[tuple[CorelessComponent, str]] = []
        # Validate every manifest and checkpoint name before mutating any
        # component, preventing a malformed peer from causing a partial restore.
        for component in targets:
            storage = getattr(component.system.machine, "storage", None)
            raw = (
                storage.objects.get(f"machine/hub/{self.hub_id}/checkpoint")
                if storage is not None else None
            )
            if raw is None:
                manifest = None
            else:
                try:
                    manifest = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid Coreless Hub checkpoint manifest for: "
                        f"{component.component_id}"
                    ) from exc
            if manifest is None:
                raise KeyError(
                    f"no committed Coreless Hub checkpoint for: {component.component_id}"
                )
            if manifest is not None:
                if not isinstance(manifest, dict):
                    raise ValueError("Coreless Hub checkpoint manifest must be an object")
                if (
                    manifest.get("version") != self.VERSION
                    or manifest.get("hub_id") != self.hub_id
                ):
                    raise ValueError("Coreless Hub checkpoint manifest mismatch")

                manifest_components = manifest.get("components")
                checkpoints = manifest.get("checkpoints")
                if (
                    not isinstance(manifest_components, (list, tuple))
                    or not all(isinstance(item, str) for item in manifest_components)
                ):
                    raise ValueError("invalid Coreless Hub component manifest")
                if tuple(manifest_components) != expected:
                    raise ValueError("Coreless Hub component composition mismatch")
                if (
                    not isinstance(checkpoints, dict)
                    or not all(
                        isinstance(key, str) and isinstance(value, str)
                        for key, value in checkpoints.items()
                    )
                ):
                    raise ValueError("invalid Coreless Hub checkpoint map")
                if set(checkpoints) != expected_checkpoints:
                    raise ValueError("Coreless Hub checkpoint coverage mismatch")
                checkpoint_name = checkpoints.get(component.component_id)
            else:
                checkpoint_name = f"{name}-{component.component_id}"
            if not checkpoint_name:
                raise KeyError(
                    f"no Coreless Hub checkpoint for: {component.component_id}"
                )
            plans.append((component, checkpoint_name))

        # Capture a local rollback point before mutating any component.
        # If a later restore fails, previously restored components are returned
        # to their exact pre-restore state.
        rollback_names: list[tuple[CorelessComponent, str]] = []
        try:
            for component, _ in plans:
                rollback_name = (
                    f"{name}-rollback-{self.hub_id}-{component.component_id}"
                )
                component.system.checkpoint(rollback_name)
                rollback_names.append((component, rollback_name))

            restored: list[str] = []
            for component, checkpoint_name in plans:
                component.system.restore(checkpoint_name)
                component.restore_identity()
                restored.append(component.component_id)
            return tuple(restored)
        except Exception:
            for component, rollback_name in reversed(rollback_names):
                try:
                    component.system.restore(rollback_name)
                    component.restore_identity()
                except Exception:
                    # Preserve the original restore failure; rollback is
                    # best-effort because the storage layer may itself fail.
                    pass
            raise

    def execute_component_vm(self, component_id: str, count: int = 1, vcpu_id: int = 0) -> int:
        """Execute a connected component VM through the Hub hypervisor boundary."""
        component = self._components.get(component_id)
        if component is None:
            raise KeyError(f"unknown component: {component_id}")
        if not component.healthy:
            raise RuntimeError("cannot execute workload on fault-isolated component")
        if self.hypervisor is None:
            raise RuntimeError("Hub has no Coreless hypervisor")
        if component.vm is None:
            raise RuntimeError("component has no Coreless VM")
        vmid = getattr(component.vm, "vmid", None)
        if vmid is None:
            raise TypeError("bound VM has no vmid")
        return self.hypervisor.step(vmid, count=count, vcpu_id=vcpu_id)

    def schedule_components(self, rounds: int = 1) -> int:
        """Run bounded round-robin scheduling for every executable component VM."""
        if self.hypervisor is None:
            raise RuntimeError("Hub has no Coreless hypervisor")
        if rounds < 1:
            raise ValueError("rounds must be positive")
        executed = 0
        for component in self.components():
            if not component.healthy or component.vm is None:
                continue
            vmid = getattr(component.vm, "vmid", None)
            if vmid is None:
                continue
            try:
                executed += self.hypervisor.schedule(vmid, rounds=rounds)
            except (RuntimeError, TypeError, KeyError):
                continue
        return executed

    def dispatch(self, workload: Workload) -> WorkloadResult:
        """Dispatch one workload through bounded, load-aware component capacity."""
        while True:
            with self._dispatch_condition:
                candidates = [
                    component
                    for component in self.components()
                    if component.healthy
                    and component.workload_executor is not None
                    and component.descriptor.supports(workload.capability)
                ]
                if not candidates:
                    advertised = [
                        component for component in self.components()
                        if component.healthy and component.descriptor.supports(workload.capability)
                    ]
                    if advertised:
                        raise RuntimeError(f"no executor available for capability: {workload.capability}")
                    raise LookupError(f"no healthy component provides capability: {workload.capability}")
                candidates.sort(key=lambda component: (
                    self._dispatch_load.get(component.component_id, 0),
                    component.component_id,
                ))
                selected = candidates[0]
                load = self._dispatch_load.get(selected.component_id, 0)
                if load < selected.descriptor.capacity:
                    self._dispatch_load[selected.component_id] = load + 1
                    break
                self._dispatch_condition.wait()
        try:
            return selected.execute_workload(workload)
        finally:
            with self._dispatch_condition:
                current = self._dispatch_load.get(selected.component_id, 0)
                self._dispatch_load[selected.component_id] = max(0, current - 1)
                self._dispatch_condition.notify_all()
    def dispatch_pipeline(
        self, workloads: tuple[Workload, ...] | list[Workload]
    ) -> tuple[WorkloadResult, ...]:
        """Execute a workload pipeline across specialized components."""
        return tuple(self.dispatch(workload) for workload in workloads)

    def dispatch_parallel(
        self, workloads: tuple[Workload, ...] | list[Workload]
    ) -> tuple[WorkloadResult, ...]:
        """Dispatch independent workloads concurrently across the Hub."""
        workload_list = tuple(workloads)
        if not workload_list:
            return ()
        capacity = sum(
            component.descriptor.capacity
            for component in self.components()
            if component.healthy and component.workload_executor is not None
        )
        max_workers = max(1, min(len(workload_list), capacity))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = tuple(
                executor.submit(self.dispatch, workload)
                for workload in workload_list
            )
            return tuple(future.result() for future in futures)

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
