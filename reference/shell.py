"""Native interactive Coreless shell."""
import shlex

class Shell:
    def __init__(self, machine, fs=None, os=None):
        self.machine = machine
        self.fs = fs or machine.filesystem
        self.os = os
        self.cwd = "/"
        self.commands = {
            "boot": self.boot,
            "cat": self.cat,
            "checkpoint": self.checkpoint,
            "checkpoints": self.checkpoints,
            "restore": self.restore,
            "clear": self.clear,
            "cpu": self.cpu,
            "desktop": self.desktop_status,
            "devices": self.devices,
            "events": self.events,
            "help": self.help,
            "kill": self.kill,
            "ls": self.ls,
            "memory": self.memory,
            "net": self.net,
            "open": self.open_window,
            "ps": self.ps,
            "pwd": self.pwd,
            "rm": self.rm,
            "run": self.run,
            "status": self.status,
            "storage": self.storage,
            "windows": self.windows,
            "write": self.write,
        }

    @property
    def processes(self):
        return self.os.processes if self.os else None

    @property
    def network(self):
        return self.os.network if self.os else None

    @property
    def desktop_service(self):
        return self.os.desktop if self.os else None

    def execute(self, line):
        try:
            p = shlex.split(line.strip())
        except ValueError as e:
            return "parse error: " + str(e)
        if not p:
            return ""
        cmd, args = p[0], p[1:]
        if cmd == "cd":
            path = self._path(args[0] if args else "/")
            if path != "/" and not any(
                x == path or x.startswith(path.rstrip("/") + "/")
                for x in self.fs.files
            ):
                return "cd: no such directory"
            self.cwd = path
            return ""
        if cmd == "exit":
            return "exit"
        if cmd not in self.commands:
            return "unknown command: " + cmd
        return self.commands[cmd](args)

    def _path(self, p):
        return self.fs._path(self.cwd + "/" + p if not p.startswith("/") else p)

    def help(self, args):
        return " ".join(sorted(set(self.commands) | {"cd", "exit"}))

    def ls(self, args):
        if len(args) > 1:
            return "usage: ls [PATH]"
        return "\n".join(self.fs.list(self._path(args[0]) if args else self.cwd))

    def pwd(self, args):
        return self.cwd

    def write(self, args):
        if len(args) < 2:
            return "usage: write PATH TEXT"
        self.fs.write(self._path(args[0]), " ".join(args[1:]).encode())
        return ""

    def cat(self, args):
        if len(args) != 1:
            return "usage: cat PATH"
        try:
            return self.fs.read(self._path(args[0])).decode()
        except (FileNotFoundError, UnicodeDecodeError):
            return "cat: unable to read"

    def rm(self, args):
        if len(args) != 1:
            return "usage: rm PATH"
        try:
            self.fs.delete(self._path(args[0]))
            return ""
        except FileNotFoundError:
            return "rm: not found"

    def run(self, args):
        if len(args) != 1:
            return "usage: run PROGRAM"
        path = self._path(args[0])
        try:
            program = self.fs.read(path)
            name = path.rsplit("/", 1)[-1] or path
            p = self.processes.create(name, program)
            self.processes.start(p.pid)
            return "pid=%d state=%s pc=%d" % (p.pid, p.state, p.pc)
        except FileNotFoundError:
            return "run: not found"
        except Exception as e:
            return "run: " + str(e)

    def ps(self, args):
        if args:
            return "usage: ps"
        if not self.processes:
            return "no process manager"
        lines = ["PID STATE NAME PC"]
        for p in self.processes.list():
            lines.append("%d %s %s %d" % (p.pid, p.state, p.name, p.pc))
        return "\n".join(lines)

    def kill(self, args):
        if len(args) != 1:
            return "usage: kill PID"
        try:
            pid = int(args[0])
            self.processes.kill(pid)
            return "killed %d" % pid
        except (ValueError, KeyError):
            return "kill: process not found"

    def net(self, args):
        if not self.network:
            return "network service unavailable"
        if not args:
            c = self.network.config
            return "link=%s ipv4=%s ipv6=%s hostname=%s" % (
                "up" if self.network.device.link_up else "down",
                c["ipv4"] or "-",
                c["ipv6"] or "-",
                c["hostname"],
            )
        if args[0] == "config":
            if len(args) == 1:
                return self.net([])
            if len(args) not in (3, 5, 7):
                return "usage: net config ipv4 ADDRESS [ipv6 ADDRESS] [hostname NAME]"
            pairs = dict(zip(args[1::2], args[2::2]))
            allowed = {"ipv4", "ipv6", "hostname"}
            if any(k not in allowed for k in pairs):
                return "net: unknown setting"
            self.network.configure(**pairs)
            return self.net([])
        if args[0] == "ping" and len(args) == 2:
            try:
                self.network.ping_frame(args[1])
                return "PING sent to " + args[1]
            except RuntimeError as e:
                return "net: " + str(e)
        if args[0] == "rx" and len(args) == 1:
            return self.network.receive() or "no packets"
        return "usage: net [config|ping|rx]"

    def desktop_status(self, args):
        if args:
            return "usage: desktop"
        d = self.desktop_service
        return "display=%dx%d windows=%d scanout=%s" % (
            d.surface.width, d.surface.height, len(d.windows),
            "ready" if self.machine.graphics.scanout is d.surface else "not-presented",
        )

    def open_window(self, args):
        if not self.desktop_service:
            return "desktop service unavailable"
        if not args:
            return "usage: open TITLE [WIDTH HEIGHT]"
        title = " ".join(args[:-2]) if len(args) >= 3 else " ".join(args)
        width, height = (int(args[-2]), int(args[-1])) if len(args) >= 3 else (320, 200)
        self.desktop_service.open_window(title, width, height)
        return "window opened: " + title

    def windows(self, args):
        if args:
            return "usage: windows"
        return "\n".join(
            "%d %s %dx%d" % (i + 1, w["title"], w["width"], w["height"])
            for i, w in enumerate(self.desktop_service.windows)
        ) or "no windows"

    def events(self, args):
        if args:
            return "usage: events"
        events = self.desktop_service.events()
        return "\n".join(map(str, events)) or "no events"

    def cpu(self, args):
        if args:
            return "usage: cpu"
        c = self.machine.cpu
        return "Coreless-64 CPUs=%d id=%d pc=%d privilege=%d halted=%s" % (
            len(self.machine.cpus), c.csrs.get(0x00A, 0), c.pc, c.privilege, c.halted
        )

    def memory(self, args):
        if args:
            return "usage: memory"
        return "memory=%d bytes" % len(self.machine.cpu.memory)

    def devices(self, args):
        if args:
            return "usage: devices"
        devices = self.machine.devices.discover()
        return "\n".join(
            "type=%d version=%d caps=%d" % (d.device_type, d.version, d.capabilities)
            for d in devices
        ) or "no devices"

    def storage(self, args):
        if args:
            return "usage: storage"
        return "objects=%d" % len(self.machine.storage.objects)

    def checkpoint(self, args):
        if len(args) > 1:
            return "usage: checkpoint [NAME]"
        name = args[0] if args else "machine"
        self.machine.checkpoint(name)
        return "checkpoint saved: " + name

    def checkpoints(self, args):
        if args:
            return "usage: checkpoints"
        return "\n".join(self.machine.list_checkpoints()) or "no checkpoints"

    def restore(self, args):
        if len(args) != 1:
            return "usage: restore NAME"
        try:
            self.machine.restore_checkpoint(args[0])
            return "restored: " + args[0]
        except KeyError:
            return "restore: checkpoint not found"

    def boot(self, args):
        if args:
            return "usage: boot"
        if self.os:
            self.os.boot()
        else:
            self.machine.boot()
        return "booted"

    def status(self, args):
        if args:
            return "usage: status"
        if self.os:
            s = self.os.status()
            return (
                "Coreless-64 %s booted=%s CPUs=%d memory=%d processes=%d "
                "network=%s windows=%d"
            ) % (
                s["version"], s["booted"], s["cpus"], s["memory"],
                s["processes"], "up" if s["link_up"] else "down", s["windows"]
            )
        return "Coreless-64 ready; CPUs=%d; booted=%s" % (
            len(self.machine.cpus), self.machine.booted
        )

    def clear(self, args):
        return "\x1b[2J\x1b[H"


    def command(self, line):
        return self.execute(line)
