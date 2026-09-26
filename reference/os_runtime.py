"""Native Coreless operating environment for the reference machine."""
from firmware import Firmware
from process import ProcessManager
from netstack import NetworkStack
from display import Desktop
from shell import Shell

class CorelessOS:
    """Boots the machine and exposes the native Coreless shell and services."""

    VERSION = "0.1"

    def __init__(self, machine):
        self.machine = machine
        self.firmware = Firmware(machine)
        self.processes = ProcessManager(machine)
        self.network = NetworkStack(machine.network)
        self.desktop = Desktop(machine.graphics)
        self.shell = Shell(machine, os=self)

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
