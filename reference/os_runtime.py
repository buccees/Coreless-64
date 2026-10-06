"""Native Coreless operating environment for the reference machine."""
from firmware import Firmware
from process import ProcessManager
from netstack import NetworkStack
from display import Desktop
from shell import Shell


class CorelessOS:
    VERSION = "0.1"
    STATE_VERSION = 2
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
        self.display_handles = {}
        self.next_display_handle = 0
        self.application_state = {}
        self._exec_transfer = False
        for cpu in self.machine.cpus:
            cpu.supervisor_trap_handler = self._supervisor_trap
        self.machine.attach_os(self)

    def save_state(self):
        return {
            "version": self.STATE_VERSION,
            "current_pid": self.current_pid,
            "init_pid": self.init_pid,
            "next_handle": self.next_handle,
            "next_display_handle": self.next_display_handle,
            "handles": {str(k): dict(v) for k, v in sorted(self.handles.items())},
            "processes": self.processes.save_state(),
            "desktop": self.desktop.save_state(),
            "application_state": {str(pid): dict(state) for pid, state in sorted(self.application_state.items())},
            "shell": {"cwd": self.shell.cwd},
        }

    def restore_state(self, state):
        if not state:
            return
        if state.get("version") not in (1, self.STATE_VERSION):
            raise ValueError("unsupported Coreless OS-state version")
        self.current_pid = state.get("current_pid", 0)
        self.init_pid = state.get("init_pid", 0)
        self.next_handle = state.get("next_handle", 3)
        self.next_display_handle = state.get("next_display_handle", 0)
        self.handles = {int(k): dict(v) for k, v in state.get("handles", {}).items()}
        self.processes.restore_state(state.get("processes"))
        self.desktop.restore_state(state.get("desktop"))
        self.application_state = {
            int(pid): dict(value)
            for pid, value in state.get("application_state", {}).items()
        }
        self.shell.cwd = state.get("shell", {}).get("cwd", "/")

    def _ret(self, cpu, value=0):
        cpu.write_reg(1, value); return value

    def _arg(self, cpu, n):
        return cpu.read_reg(n)

    def _read_user_bytes(self, cpu, addr, length):
        if length < 0 or length > (1 << 20): raise ValueError("invalid user buffer length")
        return bytes(cpu.load_u(addr + i, 1) for i in range(length))

    def _write_user_bytes(self, cpu, addr, data, limit=None):
        data = bytes(data)
        if limit is not None: data = data[:limit]
        for i, b in enumerate(data): cpu.store_u(addr + i, 1, b)
        return len(data)

    def _read_user_text(self, cpu, addr, length):
        return self._read_user_bytes(cpu, addr, length).decode("utf-8")

    def _supervisor_trap(self, cpu, trap):
        if trap.cause != "syscall": return False
        self._syscall(cpu, trap.tval)
        if cpu.halted: return True
        if self._exec_transfer:
            self._exec_transfer = False
            return True
        cpu.csrs[0x004] = (trap.pc + 4) & ((1 << 64) - 1)
        cpu.privilege = cpu._trap_saved_privilege
        cpu.csrs[0x000] = cpu.privilege
        cpu.csrs[0x001] = cpu._trap_saved_ie
        cpu.pc = cpu.csrs[0x004]
        return True

    def _syscall(self, cpu, number):
        name = self.SYSCALLS.get(number)
        if name is None: return self._ret(cpu, -1)
        if name == "exit":
            cpu.halted = True
            if self.current_pid in self.processes.processes:
                self.processes.processes[self.current_pid].state = "exited"
            return self._ret(cpu, 0)
        if name == "getpid": return self._ret(cpu, self.current_pid)
        if name == "memory": return self._ret(cpu, len(cpu.memory))
        if name == "cpu_info": return self._ret(cpu, len(self.machine.cpus))
        if name == "device_info": return self._ret(cpu, len(self.machine.devices.discover()))
        if name == "time": return self._ret(cpu, cpu.cycle)
        if name in ("yield", "sleep"): return self._ret(cpu, 0)
        if name == "kill":
            try: self.processes.kill(self._arg(cpu, 2)); return self._ret(cpu, 0)
            except KeyError: return self._ret(cpu, -1)
        if name == "checkpoint":
            try:
                name_text = self._read_user_text(cpu, self._arg(cpu, 2), self._arg(cpu, 3))
                self.machine.checkpoint(name_text or "syscall"); return self._ret(cpu, 0)
            except Exception: return self._ret(cpu, -1)
        if name == "capability": return self._ret(cpu, 1)
        if name == "open":
            try: path = self._read_user_text(cpu, self._arg(cpu, 2), self._arg(cpu, 3))
            except Exception: return self._ret(cpu, -1)
            if not self.machine.filesystem.exists(path): return self._ret(cpu, -1)
            handle = self.next_handle; self.next_handle += 1
            self.handles[handle] = {"kind":"file","path":path,"offset":0}
            return self._ret(cpu, handle)
        if name == "close":
            self.handles.pop(self._arg(cpu, 2), None); return self._ret(cpu, 0)
        if name == "read":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file": return self._ret(cpu, -1)
            try:
                data = self.machine.filesystem.read(handle["path"])
                offset = handle["offset"]; data = data[offset:offset + self._arg(cpu, 4)]
                addr = self._arg(cpu, 3)
                for i, b in enumerate(data): cpu.store_u(addr + i, 1, b)
                handle["offset"] += len(data); return self._ret(cpu, len(data))
            except Exception: return self._ret(cpu, -1)
        if name == "write":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file": return self._ret(cpu, -1)
            try:
                addr, length = self._arg(cpu, 3), self._arg(cpu, 4)
                data = bytes(cpu.load_u(addr + i, 1) for i in range(length))
                old = self.machine.filesystem.read(handle["path"]); offset = handle["offset"]
                self.machine.filesystem.write(handle["path"], old[:offset] + data + old[offset + len(data):])
                handle["offset"] += len(data); return self._ret(cpu, len(data))
            except Exception: return self._ret(cpu, -1)
        if name == "seek":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle or handle["kind"] != "file": return self._ret(cpu, -1)
            try:
                size = len(self.machine.filesystem.read(handle["path"]))
                handle["offset"] = min(self._arg(cpu, 3), size)
                return self._ret(cpu, handle["offset"])
            except Exception: return self._ret(cpu, -1)
        if name == "stat":
            handle = self.handles.get(self._arg(cpu, 2))
            if not handle: return self._ret(cpu, -1)
            try: return self._ret(cpu, len(self.machine.filesystem.read(handle["path"])))
            except Exception: return self._ret(cpu, -1)
        if name == "spawn":
            try:
                path = self._read_user_text(cpu, self._arg(cpu, 2), self._arg(cpu, 3))
                p = self.processes.spawn(path, self.machine.filesystem.read(path), parent=self.current_pid)
                self.application_state[p.pid] = {
                    "path": path, "cwd": self.shell.cwd, "argv": [path],
                    "state": "ready", "parent": self.current_pid,
                }
                return self._ret(cpu, p.pid)
            except Exception: return self._ret(cpu, -1)
        if name == "wait":
            p = self.processes.wait(self.current_pid); return self._ret(cpu, p.pid if p else 0)
        if name == "exec":
            try:
                path = self._read_user_text(cpu, self._arg(cpu, 2), self._arg(cpu, 3))
                program = self.machine.filesystem.read(path)
                if self.current_pid in self.processes.processes:
                    p = self.processes.processes[self.current_pid]
                    self.processes.replace_program(p, program)
                    self.processes.load_image(p)
                    self.processes._enter_user(p)
                    self._exec_transfer = True
                return self._ret(cpu, 0)
            except Exception: return self._ret(cpu, -1)
        if name == "net_send":
            try:
                data = self._read_user_bytes(cpu, self._arg(cpu, 2), self._arg(cpu, 3))
                target = self._read_user_text(cpu, self._arg(cpu, 4), self._arg(cpu, 5))
                return self._ret(cpu, len(self.network.device.transmit(data, target).data))
            except Exception: return self._ret(cpu, -1)
        if name == "net_recv":
            packet = self.network.device.poll_rx()
            if packet is None: return self._ret(cpu, 0)
            for i, b in enumerate(packet.data): cpu.store_u(self._arg(cpu, 2) + i, 1, b)
            return self._ret(cpu, len(packet.data))
        if name == "display_open":
            try:
                surface = self.machine.graphics.create_surface(self._arg(cpu, 2), self._arg(cpu, 3))
                handle = self.next_display_handle; self.next_display_handle += 1
                self.display_handles[handle] = surface; return self._ret(cpu, handle)
            except Exception: return self._ret(cpu, -1)
        if name == "display_present":
            try:
                surface = self.display_handles[self._arg(cpu, 2)]
                surface.ready = True; self.machine.graphics.present(surface); return self._ret(cpu, 0)
            except Exception: return self._ret(cpu, -1)
        if name == "input_read":
            event = self.machine.graphics.poll_input()
            if event is None: return self._ret(cpu, 0)
            try:
                payload = repr(event).encode("utf-8")
                return self._ret(cpu, self._write_user_bytes(cpu, self._arg(cpu, 2), payload, self._arg(cpu, 3)))
            except Exception: return self._ret(cpu, -1)
        return self._ret(cpu, -1)

    def start_init(self, program_path="/init"):
        if not self.machine.filesystem.exists(program_path):
            raise FileNotFoundError(program_path)
        if self.init_pid in self.processes.processes:
            self.current_pid = self.init_pid
            return self.processes.processes[self.init_pid]
        p = self.processes.create("init", self.machine.filesystem.read(program_path), parent=0)
        self.init_pid = p.pid; self.current_pid = p.pid
        self.application_state[p.pid] = {
            "path": program_path, "cwd": self.shell.cwd, "argv": [program_path],
            "state": "ready", "parent": 0,
        }
        self.processes._enter_user(p)
        return p

    def boot(self):
        resuming = self.machine.power_state == "on" and self.machine.booted
        self.firmware.initialize()
        if resuming:
            self.firmware.status["boot"] = True
            for cpu in self.machine.cpus:
                cpu.csrs[0x01D] = 2
        else:
            self.firmware.boot(None)
        self.network.device.configure(link_up=True, features=self.machine.network.features)
        self.machine.booted = True
        self.machine.power_state = "on"
        if not resuming and self.init_pid == 0 and self.machine.filesystem.exists("/init"):
            self.start_init("/init")
        self.machine.save_state()
        return self

    def resume(self):
        if not self.machine.booted or self.machine.power_state != "on":
            return self.boot()
        return self.boot()

    def cold_boot(self):
        self.machine.booted = False
        self.machine.power_state = "off"
        return self.boot()

    def command(self, line):
        return self.shell.execute(line)

    def run(self):
        return self.boot()

    def status(self):
        return {
            "version": self.VERSION, "booted": self.machine.booted,
            "power_state": self.machine.power_state,
            "cpus": len(self.machine.cpus), "memory": len(self.machine.cpu.memory),
            "processes": len(self.processes.processes),
            "network": self.network.config.copy(), "link_up": self.network.device.link_up,
            "windows": len(self.desktop.windows),
        }
