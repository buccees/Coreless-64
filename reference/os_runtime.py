"""Native Coreless operating environment for the reference machine."""
from firmware import Firmware
from process import ProcessManager
from netstack import NetworkStack
from display import Desktop
from shell import Shell

class CorelessOS:
    """Boots the machine and exposes the native Coreless shell and services."""

    VERSION = "0.1"
    SYSCALLS = {
        0:"exit", 1:"read", 2:"write", 3:"open", 4:"close", 5:"seek",
        6:"stat", 7:"sleep", 8:"yield", 9:"spawn", 10:"exec", 11:"wait",
        12:"kill", 13:"getpid", 14:"time", 15:"memory", 16:"cpu_info",
        17:"device_info", 18:"net_send", 19:"net_recv", 20:"socket",
        21:"connect", 22:"listen", 23:"accept", 24:"display_open",
        25:"display_present", 26:"input_read", 27:"checkpoint", 28:"capability",
    }

    def __init__(self, machine):
        self.machine = machine
        self.firmware = Firmware(machine)
        self.processes = ProcessManager(machine)
        self.network = NetworkStack(machine.network)
        self.desktop = Desktop(machine.graphics)
        self.shell = Shell(machine, os=self)
        self.current_pid = 0
        self.init_pid = 0
        self.handles = {}
        self.next_handle = 3
        for cpu in self.machine.cpus:
            cpu.syscall_handler = self._syscall

    def _ret(self, cpu, value=0):
        cpu.write_reg(1, value)
        return value

    def _arg(self, cpu, n):
        return cpu.read_reg(n)

    def _syscall(self, cpu, number):
        name = self.SYSCALLS.get(number)
        if name is None:
            return self._ret(cpu, -1)

        if name == "exit":
            cpu.halted = True
            if self.current_pid in self.processes.processes:
                self.processes.processes[self.current_pid].state = "exited"
            return self._ret(cpu, 0)

        if name == "getpid":
            return self._ret(cpu, self.current_pid)

        if name == "memory":
            return self._ret(cpu, len(cpu.memory))

        if name == "cpu_info":
            return self._ret(cpu, len(self.machine.cpus))

        if name == "device_info":
            return self._ret(cpu, len(self.machine.devices.discover()))

        if name == "time":
            return self._ret(cpu, cpu.cycle)

        if name in ("yield", "sleep"):
            return self._ret(cpu, 0)

        if name == "kill":
            try:
                self.processes.kill(self._arg(cpu, 2))
                return self._ret(cpu, 0)
            except KeyError:
                return self._ret(cpu, -1)

        if name == "checkpoint":
            self.machine.checkpoint("syscall-%d" % self._arg(cpu, 2))
            return self._ret(cpu, 0)

        if name == "capability":
            return self._ret(cpu, 1)

        if name == "open":
            path = self._arg(cpu, 2)
            if not isinstance(path, str):
                return self._ret(cpu, -1)
            if not self.machine.filesystem.exists(path):
                return self._ret(cpu, -1)
            handle = self.next_handle
            self.next_handle += 1
            self.handles[handle] = {"kind": "file", "path": path, "offset": 0}
            return self._ret(cpu, handle)

        if name == "close":
            self.handles.pop(self._arg(cpu, 2), None)
            return self._ret(cpu, 0)

        if name == "read":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file":
                return self._ret(cpu, -1)
            try:
                data = self.machine.filesystem.read(handle["path"])
                offset = handle["offset"]
                length = self._arg(cpu, 4)
                data = data[offset:offset + length]
                addr = self._arg(cpu, 3)
                for i, b in enumerate(data):
                    cpu.store_u(addr + i, 1, b)
                handle["offset"] += len(data)
                return self._ret(cpu, len(data))
            except Exception:
                return self._ret(cpu, -1)

        if name == "write":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file":
                return self._ret(cpu, -1)
            try:
                addr = self._arg(cpu, 3)
                length = self._arg(cpu, 4)
                data = bytes(cpu.load_u(addr + i, 1) for i in range(length))
                old = self.machine.filesystem.read(handle["path"])
                offset = handle["offset"]
                new = old[:offset] + data + old[offset + len(data):]
                self.machine.filesystem.write(handle["path"], new)
                handle["offset"] += len(data)
                return self._ret(cpu, len(data))
            except Exception:
                return self._ret(cpu, -1)

        if name == "seek":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file":
                return self._ret(cpu, -1)
            offset = self._arg(cpu, 3)
            try:
                size = len(self.machine.filesystem.read(handle["path"]))
                handle["offset"] = min(offset, size)
                return self._ret(cpu, handle["offset"])
            except Exception:
                return self._ret(cpu, -1)

        if name == "stat":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle:
                return self._ret(cpu, -1)
            try:
                return self._ret(cpu, len(self.machine.filesystem.read(handle["path"])))
            except Exception:
                return self._ret(cpu, -1)

        if name == "spawn":
            program_path = self._arg(cpu, 2)
            if not isinstance(program_path, str):
                return self._ret(cpu, -1)
            try:
                program = self.machine.filesystem.read(program_path)
                p = self.processes.spawn(program_path, program, parent=self.current_pid)
                return self._ret(cpu, p.pid)
            except Exception:
                return self._ret(cpu, -1)

        if name == "wait":
            p = self.processes.wait(self.current_pid)
            return self._ret(cpu, p.pid if p else 0)

        if name == "exec":
            program_path = self._arg(cpu, 2)
            if not isinstance(program_path, str):
                return self._ret(cpu, -1)
            try:
                program = self.machine.filesystem.read(program_path)
                self.machine.loader.load(program, 0)
                return self._ret(cpu, 0)
            except Exception:
                return self._ret(cpu, -1)

        if name == "net_send":
            try:
                addr = self._arg(cpu, 2)
                length = self._arg(cpu, 3)
                target = self._arg(cpu, 4)
                data = bytes(cpu.load_u(addr + i, 1) for i in range(length))
                packet = self.network.device.transmit(data, target if isinstance(target, str) else "")
                return self._ret(cpu, len(packet.data))
            except Exception:
                return self._ret(cpu, -1)

        if name == "net_recv":
            packet = self.network.device.poll_rx()
            if packet is None:
                return self._ret(cpu, 0)
            addr = self._arg(cpu, 2)
            for i, b in enumerate(packet.data):
                cpu.store_u(addr + i, 1, b)
            return self._ret(cpu, len(packet.data))

        if name == "display_open":
            width = self._arg(cpu, 2)
            height = self._arg(cpu, 3)
            try:
                surface = self.machine.graphics.create_surface(width, height)
                return self._ret(cpu, self.machine.graphics.surfaces.index(surface))
            except Exception:
                return self._ret(cpu, -1)

        if name == "display_present":
            index = self._arg(cpu, 2)
            try:
                surface = self.machine.graphics.surfaces[index]
                surface.ready = True
                self.machine.graphics.present(surface)
                return self._ret(cpu, 0)
            except Exception:
                return self._ret(cpu, -1)

        if name == "input_read":
            event = self.machine.graphics.poll_input()
            if event is None:
                return self._ret(cpu, 0)
            return self._ret(cpu, 1)

        return self._ret(cpu, -1)

    def start_init(self, program_path="/init"):
        if not self.machine.filesystem.exists(program_path):
            raise FileNotFoundError(program_path)
        program = self.machine.filesystem.read(program_path)
        p = self.processes.create("init", program, parent=0)
        self.init_pid = p.pid
        self.current_pid = p.pid
        return p

    def boot(self):

        self.firmware.initialize()
        self.firmware.boot()
        self.network.device.configure(link_up=True)
        return self

    def command(self, line):
        return self.shell.execute(line)

    def run(self):
        self.boot()
        return self.shell

    def status(self):
        return {
            "version": self.VERSION,
            "booted": self.machine.booted,
            "cpus": len(self.machine.cpus),
            "memory": len(self.machine.cpu.memory),
            "processes": len(self.processes.processes),
            "network": self.network.config.copy(),
            "link_up": self.network.device.link_up,
            "windows": len(self.desktop.windows),
        }
