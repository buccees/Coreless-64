"""Policy-bound adapters from 314DNest actions to Coreless resources.

The controller exposes only explicitly registered operations. Every operation
still passes through DeterministicPolicy and a capability check before the
underlying Coreless interface is touched.
"""

from __future__ import annotations

from typing import Any, Mapping

from .interfaces import ComputeInterface, IOInterface, MemoryInterface, StorageInterface
from .policy import DeterministicPolicy
from .interfaces import AuthorityLevel


class CorelessResourceController:
    def __init__(
        self,
        policy: DeterministicPolicy,
        *,
        compute: ComputeInterface | None = None,
        memory: MemoryInterface | None = None,
        storage: StorageInterface | None = None,
        io: IOInterface | None = None,
        hypervisor: Any | None = None,
    ) -> None:
        self.policy = policy
        self.compute = compute
        self.memory = memory
        self.storage = storage
        self.io = io
        self.hypervisor = hypervisor

    def bind_coreless_machine(self, machine: Any) -> None:
        """Bind the controller directly to a reference CorelessMachine."""
        self.compute = _MachineCompute(machine)
        self.memory = _MachineMemory(machine.cpu.memory)
        self.storage = _MachineStorage(machine.storage)
        self.io = _MachineIO(machine)
        self.register_defaults()

    def bind_hypervisor(self, hypervisor: Any) -> None:
        self.hypervisor = hypervisor
        self.policy.register("vm.start", self._vm_start)
        self.policy.register("vm.stop", self._vm_stop)

    def register_defaults(self) -> None:
        self._require(self.compute, "compute")
        self.policy.register("compute.submit", self._compute_submit)
        if self.memory is not None:
            self.policy.register("memory.write", self._memory_write)
        if self.storage is not None:
            self.policy.register("storage.write", self._storage_write)
        if self.io is not None:
            self.policy.register("io.emit", self._io_emit)
        if self.hypervisor is not None:
            self.policy.register("vm.start", self._vm_start)
            self.policy.register("vm.stop", self._vm_stop)

    def grant(self, operation: str, capability: str) -> None:
        self.policy.grant_capability(capability, operation)

    def execute(self, proposal):
        return self.policy.execute(proposal)

    @staticmethod
    def _require(resource: object | None, name: str) -> None:
        if resource is None:
            raise ValueError(f"{name} interface is required")

    def _compute_submit(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.compute, "compute")
        job_id = self.compute.submit(str(args["operation"]), dict(args.get("payload", {})))
        return {"job_id": job_id}

    def _memory_write(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.memory, "memory")
        data = args["data"]
        if isinstance(data, str):
            data = data.encode()
        self.memory.write(int(args["address"]), bytes(data))
        return {"written": len(data)}

    def _storage_write(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.storage, "storage")
        data = args["data"]
        if isinstance(data, str):
            data = data.encode()
        self.storage.write(str(args["key"]), bytes(data))
        return {"key": str(args["key"]), "written": len(data)}

    def _io_emit(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.io, "io")
        self.io.emit(str(args["device"]), dict(args.get("payload", {})))
        return {"device": str(args["device"]), "emitted": True}

    def _vm_start(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.hypervisor, "hypervisor")
        vmid = int(args["vmid"])
        self.hypervisor.run(vmid)
        return {"vmid": vmid, "running": True}

    def _vm_stop(self, args: Mapping[str, Any]) -> Mapping[str, Any]:
        self._require(self.hypervisor, "hypervisor")
        vmid = int(args["vmid"])
        self.hypervisor.stop(vmid)
        return {"vmid": vmid, "running": False}


class _MachineCompute:
    def __init__(self, machine: Any) -> None:
        self.machine = machine

    def submit(self, operation: str, payload: Mapping[str, Any]) -> str:
        if operation == "step":
            count = max(1, int(payload.get("count", 1)))
            for _ in range(count):
                self.machine.cpu.step()
            return f"cpu:{self.machine.cpu.cpu_id if hasattr(self.machine.cpu, 'cpu_id') else 0}:step"
        if operation == "load_program":
            program = payload["program"]
            if isinstance(program, str):
                program = bytes.fromhex(program)
            self.machine.load_program(bytes(program), int(payload.get("address", 0)))
            return "program:loaded"
        raise ValueError("unsupported Coreless compute operation")


class _MachineMemory:
    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def read(self, address: int, size: int) -> bytes:
        return bytes(self.memory[address:address + size])

    def write(self, address: int, data: bytes) -> None:
        self.memory[address:address + len(data)] = bytes(data)
        self.memory.flush()


class _MachineStorage:
    def __init__(self, storage: Any) -> None:
        self.storage = storage

    def read(self, key: str) -> bytes:
        return self.storage.get(key)

    def write(self, key: str, data: bytes) -> None:
        self.storage.put(key, data)


class _MachineIO:
    def __init__(self, machine: Any) -> None:
        self.machine = machine

    def emit(self, device: str, payload: Mapping[str, Any]) -> None:
        if device == "network":
            self.machine.network.transmit(bytes(payload["data"]), str(payload.get("destination", "")))
            return
        if device == "graphics":
            self.machine.graphics.submit(dict(payload))
            return
        raise ValueError("unsupported Coreless device")
