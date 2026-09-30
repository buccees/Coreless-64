"""Integrated Coreless-64 reference machine runtime."""
import json

from core import CorelessCPU
from machine import InterruptController, DeviceFabric, Device
from storage import PersistentMachineImage
from device_io import NetworkDevice, GraphicsDevice, DisplaySurface
from filesystem import FileSystem
from loader import ProgramLoader
from ai.compute_fabric import AIComputeFabric, ComputeWork, ComputeResult, RegisteredAICoreResource
from ai.registry import AICoreRegistry
from ai.interfaces import AIResult
from ai.telemetry import TelemetryProvider
from machine_work_distribution import MachineWorkDistributor
from scheduler import MachineScheduler, ConventionalComputeResource, AIComputeSchedulerResource


class CorelessMachine:
    STATE_VERSION = 3

    def __init__(self, memory_size=1 << 20, cpu_count=1, storage_path=None):
        if cpu_count < 1:
            raise ValueError("cpu_count must be positive")
        if memory_size < 4096 or memory_size % 4096:
            raise ValueError("Coreless RAM size must be a positive 4 KiB multiple")
        self.storage = PersistentMachineImage(storage_path)
        # All CPUs observe one Coreless RAM instance.  The reference machine
        # therefore has one architectural memory, not one cache per CPU.
        from memory import VirtualRAM
        shared_memory = VirtualRAM(memory_size, self.storage, "ram")
        self.cpus = [CorelessCPU(memory_size, storage=self.storage, memory_name="ram",
                                 memory=shared_memory)
                     for _ in range(cpu_count)]
        for i, cpu in enumerate(self.cpus):
            cpu.csrs[0x00A] = i
            cpu.csrs[0x00B] = cpu_count
        self.interrupts = InterruptController(cpu_count)
        self.devices = DeviceFabric()
        self.devices.attach_interrupt_controller(self.interrupts)
        self.devices.add(Device(1, 1, 0))
        self.devices.add(Device(2, 1, 0))
        self.network = NetworkDevice()
        self.graphics = GraphicsDevice()
        self.filesystem = FileSystem(self.storage)
        self.loader = ProgramLoader(self)
        # AI is a native machine resource. Conventional components remain
        # available; AI can augment or replace individual computational jobs.
        self.ai_fabric = AIComputeFabric()
        self.ai_registry = None
        self.telemetry = TelemetryProvider()
        self.scheduler = MachineScheduler(telemetry=self.telemetry)
        self.work_distributor = MachineWorkDistributor(self.scheduler)
        self.scheduler.register(ConventionalComputeResource(
            "cpu",
            self._conventional_compute,
            capabilities=("cpu.step", "load_program"),
        ))
        self.booted = False
        self.power_state = "off"
        self.os_runtime = None
        self._restore_machine_state()

    def publish_telemetry(self):
        """Publish current machine resource state for scheduler decisions."""
        cpu_load = {"cpu": float(self.scheduler.load("cpu"))}
        workloads = {
            resource_id: float(self.scheduler.load(resource_id))
            for resource_id in self.scheduler.resources()
            if resource_id.startswith("ai:")
        }
        return self.telemetry.publish(
            cpu=cpu_load,
            memory={"ram_bytes": float(len(self.cpu.memory))},
            storage={"objects": float(len(self.storage.objects))},
            workloads=workloads,
            vms={},
        )

    @property
    def cpu(self):
        return self.cpus[0]

    def attach_os(self, os_runtime):
        self.os_runtime = os_runtime
        raw = self.storage.objects.get("machine/os")
        if raw:
            os_runtime.restore_state(json.loads(raw.decode("utf-8")))

    def load_program(self, program, address=0):
        end = address + len(program)
        if address < 0 or end > len(self.cpu.memory):
            raise ValueError("program outside memory")
        self.cpu.memory[address:end] = program
        self.cpu.memory.flush()
        self.cpu.pc = address

    def _conventional_compute(self, work: ComputeWork) -> ComputeResult:
        if work.operation == "cpu.step":
            count = max(1, int(work.request.context.get("count", 1)))
            for _ in range(count):
                self.cpu.step()
            return ComputeResult(
                work.work_id, work.operation, "cpu",
                AIResult(
                    work.request.request_id,
                    "cpu",
                    "conventional CPU execution complete",
                    {"resource": "cpu"},
                ),
            )
        if work.operation == "load_program":
            program = work.request.context["program"]
            if isinstance(program, str):
                program = bytes.fromhex(program)
            self.load_program(bytes(program), int(work.request.context.get("address", 0)))
            return ComputeResult(
                work.work_id, work.operation, "cpu",
                AIResult(
                    work.request.request_id,
                    "cpu",
                    "program loaded",
                    {"resource": "cpu"},
                ),
            )
        raise ValueError("unsupported conventional compute operation")

    def distribute_work(self, items, *, preference="balanced", allow_fallback=True):
        """Execute independent work through the unified machine resource pool."""
        self.publish_telemetry()
        results = self.work_distributor.execute(items, preference=preference, allow_fallback=allow_fallback)
        self.publish_telemetry()
        return results

    def schedule_compute(self, work: ComputeWork, *, preference="balanced",
                         allow_fallback=True):
        """Allocate work across conventional and AI machine resources."""
        return self.scheduler.execute(
            work, preference=preference, allow_fallback=allow_fallback
        )

    def attach_ai_registry(self, registry: AICoreRegistry, model_ids=None):
        """Expose registered AI cores as native Coreless compute resources."""
        selected = tuple(model_ids) if model_ids is not None else registry.enabled_cores()
        for model_id in selected:
            self.ai_fabric.register(RegisteredAICoreResource(registry, model_id))
            self.scheduler.register(AIComputeSchedulerResource(
                self.ai_fabric,
                model_id,
                capabilities=(
                    "tensor.matmul",
                    "tensor.linear",
                    "tensor.softmax",
                    "transformer.attention",
                    "transformer.block",
                    "ai.infer",
                ),
            ))
        self.ai_registry = registry
        return self.ai_fabric.resources()

    def ai_compute(self, work: ComputeWork, model_id: str) -> ComputeResult:
        """Dispatch a machine workload through the AI computational fabric."""
        return self.ai_fabric.compute(work, model_id)

    @staticmethod
    def _cpu_state(cpu):
        return {
            "r": cpu.r[:], "f": cpu.f[:], "fp_rounding": cpu.fp_rounding, "pc": cpu.pc, "sp": cpu.sp,
            "privilege": cpu.privilege, "halted": cpu.halted,
            "cycle": cpu.cycle, "instret": cpu.instret,
            "csrs": {str(k): v for k, v in cpu.csrs.items()},
            "pending_interrupts": cpu.pending_interrupts,
            "reservation": cpu.reservation,
            "vector": cpu.vector, "vector_vl": cpu.vector_vl,
            "vector_vstart": cpu.vector_vstart, "vector_vtype": cpu.vector_vtype,
            "vector_mask": cpu.vector_mask, "matrix": cpu.matrix,
            "matrix_shape": cpu.matrix_shape,
            "tlb": {str(k): v for k, v in cpu.tlb.items()},
        }

    def _restore_cpu_state(self, cpu, state):
        cpu.r = list(state.get("r", cpu.r)); cpu.r[0] = 0
        cpu.f = list(state.get("f", cpu.f))
        cpu.fp_rounding = state.get("fp_rounding", cpu.fp_rounding)
        cpu.pc = state.get("pc", cpu.pc); cpu.sp = state.get("sp", cpu.sp)
        cpu.privilege = state.get("privilege", cpu.privilege)
        cpu.halted = state.get("halted", cpu.halted)
        cpu.cycle = state.get("cycle", cpu.cycle); cpu.instret = state.get("instret", cpu.instret)
        cpu.csrs.update({int(k): v for k, v in state.get("csrs", {}).items()})
        cpu.pending_interrupts = state.get("pending_interrupts", cpu.pending_interrupts)
        cpu.reservation = tuple(state["reservation"]) if state.get("reservation") is not None else None
        cpu.vector = state.get("vector", cpu.vector)
        cpu.vector_vl = state.get("vector_vl", cpu.vector_vl)
        cpu.vector_vstart = state.get("vector_vstart", cpu.vector_vstart)
        cpu.vector_vtype = state.get("vector_vtype", cpu.vector_vtype)
        cpu.vector_mask = state.get("vector_mask", cpu.vector_mask)
        cpu.matrix = state.get("matrix", cpu.matrix)
        cpu.matrix_shape = tuple(state.get("matrix_shape", cpu.matrix_shape))
        cpu.tlb = {int(k): v for k, v in state.get("tlb", {}).items()}

    @staticmethod
    def _packet_state(packet):
        return {"data": packet.data.hex(), "source": packet.source, "destination": packet.destination}

    def _device_state(self):
        return {
            "network": {
                "link_up": self.network.link_up,
                "features": sorted(self.network.features),
                "rx": [self._packet_state(p) for p in self.network.rx],
                "tx": [self._packet_state(p) for p in self.network.tx],
            },
            "graphics": {
                "surfaces": [
                    {"width": s.width, "height": s.height, "pixel_format": s.pixel_format,
                     "pixels": bytes(s.pixels).hex(), "ready": s.ready}
                    for s in self.graphics.surfaces
                ],
                "scanout": self.graphics.surfaces.index(self.graphics.scanout)
                    if self.graphics.scanout in self.graphics.surfaces else None,
                "input_events": list(self.graphics.input_events),
                "commands": list(self.graphics.commands),
            },
        }

    def _restore_device_state(self, state):
        from device_io import Packet
        network = state.get("network", {})
        self.network.configure(bool(network.get("link_up", False)), network.get("features", ()))
        self.network.rx = [Packet(bytes.fromhex(p.get("data", "")), p.get("source", ""),
                                  p.get("destination", "")) for p in network.get("rx", [])]
        self.network.tx = [Packet(bytes.fromhex(p.get("data", "")), p.get("source", ""),
                                  p.get("destination", "")) for p in network.get("tx", [])]
        graphics = state.get("graphics", {})
        self.graphics.surfaces = [
            DisplaySurface(s["width"], s["height"], s.get("pixel_format", "XRGB8888"),
                           bytearray.fromhex(s.get("pixels", "")), bool(s.get("ready", False)))
            for s in graphics.get("surfaces", [])
        ]
        index = graphics.get("scanout")
        self.graphics.scanout = (self.graphics.surfaces[index]
                                 if isinstance(index, int) and 0 <= index < len(self.graphics.surfaces)
                                 else None)
        self.graphics.input_events = list(graphics.get("input_events", []))
        self.graphics.commands = list(graphics.get("commands", []))

    def save_state(self):
        for cpu in self.cpus:
            cpu.memory.flush()
        state = {
            "version": self.STATE_VERSION,
            "booted": self.booted,
            "power_state": self.power_state,
            "cpus": [self._cpu_state(cpu) for cpu in self.cpus],
            "devices": self._device_state(),
        }
        self.storage.put("machine/devices",
                         json.dumps(state["devices"], sort_keys=True, separators=(",", ":")).encode(),
                         sync=False)
        if self.os_runtime is not None:
            self.storage.put("machine/os",
                             json.dumps(self.os_runtime.save_state(), sort_keys=True, separators=(",", ":")).encode(),
                             sync=False)
        return self.storage.save_machine_state(state)

    def _restore_machine_state(self):
        state = self.storage.load_machine_state()
        if not state:
            return
        if state.get("version") not in (1, 2, self.STATE_VERSION):
            raise ValueError("unsupported Coreless machine-state version")
        saved_cpus = state.get("cpus", [])
        if len(saved_cpus) != len(self.cpus):
            raise ValueError("Coreless machine image CPU count does not match runtime")
        self.booted = bool(state.get("booted", False))
        self.power_state = state.get("power_state", "on" if self.booted else "off")
        for cpu, cpu_state in zip(self.cpus, saved_cpus):
            self._restore_cpu_state(cpu, cpu_state)
        device_state = state.get("devices")
        if device_state is None:
            raw = self.storage.objects.get("machine/devices")
            device_state = json.loads(raw.decode("utf-8")) if raw else {}
        self._restore_device_state(device_state)

    def boot(self, program=None, address=0):
        if program is not None:
            self.load_program(program, address)
        self.booted = True
        self.power_state = "on"
        self.save_state()
        return self.cpu

    def step(self, cpu_id=0):
        if not self.booted:
            raise RuntimeError("machine not booted")
        result = self.cpus[cpu_id].step()
        self.cpus[cpu_id].memory.flush()
        self.save_state()
        return result

    def run(self, max_steps=100000, cpu_id=0):
        if not self.booted:
            raise RuntimeError("machine not booted")
        steps = 0
        while steps < max_steps and not self.cpus[cpu_id].halted:
            self.cpus[cpu_id].step()
            steps += 1
        for cpu in self.cpus:
            cpu.memory.flush()
        self.save_state()
        return steps

    def run_program(self, path):
        program = self.filesystem.read(path)
        self.loader.load(program, 0)
        self.booted = True
        self.power_state = "on"
        return str(self.run())

    def checkpoint(self, name="machine"):
        """Create a complete persistent snapshot of the Coreless machine image."""
        self.save_state()
        return self.storage.create_checkpoint(name)

    def restore_checkpoint(self, name="machine"):
        """Restore the complete machine image from a persistent checkpoint."""
        self.storage.restore_checkpoint(name)
        for cpu in self.cpus:
            cpu.memory.cache.clear()
            cpu.memory.dirty.clear()
        self._restore_machine_state()
        self.filesystem.reload()
        if self.os_runtime is not None:
            raw = self.storage.objects.get("machine/os")
            if raw:
                self.os_runtime.restore_state(json.loads(raw.decode("utf-8")))
        return self

    def list_checkpoints(self):
        return self.storage.list_checkpoints()

    def shutdown(self):
        self.booted = False
        self.power_state = "off"
        return self.save_state()
