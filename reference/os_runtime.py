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
        return self._ret(cpu, -1)

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
