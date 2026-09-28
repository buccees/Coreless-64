"""Integrated Coreless-64 reference machine runtime."""
import json

from core import CorelessCPU
from machine import InterruptController, DeviceFabric, Device
from storage import PersistentMachineImage
from device_io import NetworkDevice, GraphicsDevice, DisplaySurface
from filesystem import FileSystem
from loader import ProgramLoader


class CorelessMachine:
    STATE_VERSION = 3

    def __init__(self, memory_size=1 << 20, cpu_count=1, storage_path=None):
        if cpu_count < 1:
            raise ValueError("cpu_count must be positive")
        if memory_size < 4096 or memory_size % 4096:
            raise ValueError("Coreless RAM size must be a positive 4 KiB multiple")

        self.storage = PersistentMachineImage(storage_path)
        self.cpus = [
            CorelessCPU(memory_size, storage=self.storage, memory_name="ram")
            for _ in range(cpu_count)
        ]
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
        self.booted = False
        self.power_state = "off"
        self.os_runtime = None
        self._restore_machine_state()

    @property
    def cpu(self):
        return self.cpus[0]

    def attach_os(self, os_runtime):
        self.os_runtime = os_runtime
        state = self.storage.objects.get("machine/os")
        if state:
            os_runtime.restore_state(json.loads(state.decode("utf-8")))

    @staticmethod
    def _surface_state(surface):
        return {
            "width": surface.width,
            "height": surface.height,
            "pixel_format": surface.pixel_format,
            "pixels": bytes(surface.pixels).hex(),
            "ready": surface.ready,
        }

    def _graphics_state(self):
        return {
            "surfaces": [self._surface_state(s) for s in self.graphics.surfaces],
            "scanout": self.graphics.surfaces.index(self.graphics.scanout)
                if self.graphics.scanout in self.graphics.surfaces else None,
            "input_events": list(self.graphics.input_events),
            "commands": list(self.graphics.commands),
        }

    def _restore_graphics_state(self, state):
        self.graphics.surfaces = []
        for item in state.get("surfaces", []):
            surface = DisplaySurface(
                item["width"], item["height"], item.get("pixel_format", "XRGB8888"),
                bytearray.fromhex(item.get("pixels", "")),
                bool(item.get("ready", False)),
            )
            self.graphics.surfaces.append(surface)
        index = state.get("scanout")
        self.graphics.scanout = (
            self.graphics.surfaces[index]
            if isinstance(index, int) and 0 <= index < len(self.graphics.surfaces)
            else None
        )
        self.graphics.input_events = list(state.get("input_events", []))
        self.graphics.commands = list(state.get("commands", []))

    def _device_state(self):
        return {
            "network": {
                "link_up": self.network.link_up,
                "features": sorted(self.network.features),
                "rx": [
                    {"data": p.data.hex(), "source": p.source, "destination": p.destination}
                    for p in self.network.rx
                ],
                "tx": [
                    {"data": p.data.hex(), "source": p.source, "destination": p.destination}
                    for p in self.network.tx
                ],
            },
            "graphics": self._graphics_state(),
        }

    def _restore_device_state(self, state):
        network = state.get("network", {})
        self.network.configure(
            link_up=bool(network.get("link_up", False)),
            features=network.get("features", ()),
        )
        from device_io import Packet
        self.network.rx = [
            Packet(bytes.fromhex(p.get("data", "")), p.get("source", ""), p.get("destination", ""))
            for p in network.get("rx", [])
        ]
        self.network.tx = [
            Packet(bytes.fromhex(p.get("data", "")), p.get("source", ""), p.get("destination", ""))
            for p in network.get("tx", [])
        ]
        self._restore_graphics_state(state.get("graphics", {}))

    def load_program(self, program, address=0):
        end = address + len(program)
        if address < 0 or end > len(self.cpu.memory):
            raise ValueError("program outside memory")
        self.cpu.memory[address:end] = program
        self.cpu.memory.flush()
        self.cpu.pc = address

    @staticmethod
    def _cpu_state(cpu):
        return {
            "r": cpu.r[:],
            "pc": cpu.pc,
            "sp": cpu.sp,
            "privilege": cpu.privilege,
            "halted": cpu.halted,
            "cycle": cpu.cycle,
            "instret": cpu.instret,
            "csrs": {str(k): v for k, v in cpu.csrs.items()},
            "pending_interrupts": cpu.pending_interrupts,
            "reservation": cpu.reservation,
            "vector": cpu.vector,
            "vector_vl": cpu.vector_vl,
            "vector_vstart": cpu.vector_vstart,
            "vector_vtype": cpu.vector_vtype,
            "vector_mask": cpu.vector_mask,
            "matrix": cpu.matrix,
            "matrix_shape": cpu.matrix_shape,
            "tlb": {str(k): v for k, v in cpu.tlb.items()},
        }

    def _restore_cpu_state(self, cpu, state):
        cpu.r = list(state.get("r", cpu.r))
        cpu.r[0] = 0
        cpu.pc = state.get("pc", cpu.pc)
        cpu.sp = state.get("sp", cpu.sp)
        cpu.privilege = state.get("privilege", cpu.privilege)
        cpu.halted = state.get("halted", cpu.halted)
        cpu.cycle = state.get("cycle", cpu.cycle)
        cpu.instret = state.get("instret", cpu.instret)
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
        self.storage.put("machine/devices", json.dumps(
            state["devices"], sort_keys=True, separators=(",", ":")
        ).encode(), sync=False)
        if self.os_runtime is not None:
            self.storage.put(
                "machine/os",
                json.dumps(self.os_runtime.save_state(), sort_keys=True, separators=(",", ":")).encode(),
                sync=False,
            )
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
        self.save_state()
        state = self.storage.load_machine_state()
        return self.storage.checkpoint(name, state)

    def shutdown(self):
        self.power_state = "off"
        self.booted = False
        return self.save_state()
