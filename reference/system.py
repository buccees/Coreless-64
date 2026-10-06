"""Unified Coreless digital-machine lifecycle.

This module assembles the reference CPU, persistent machine image, firmware,
native operating environment, process model, devices, and shell into one
reproducible software machine. It is the pre-hardware integration boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

from machine_runtime import CorelessMachine
from os_runtime import CorelessOS
from ai.machine_runtime import PersistentAIRuntime


class CorelessSystem:
    """Complete software Coreless machine lifecycle.

    The system remains entirely digital: the machine image carries persistent
    state, while the reference execution engine supplies computation.
    """

    VERSION = 1
    BOOT_OBJECT = "machine/boot"

    def __init__(
        self,
        machine: CorelessMachine | None = None,
        *,
        memory_size: int = 1 << 20,
        cpu_count: int = 1,
        storage_path: str | Path | None = None,
    ):
        self.machine = machine or CorelessMachine(
            memory_size=memory_size,
            cpu_count=cpu_count,
            storage_path=storage_path,
        )
        self.os = CorelessOS(self.machine)
        self.ai = PersistentAIRuntime(self.machine.storage)
        self.ai.restore()
        self._restore_boot_manifest()

    def _boot_manifest(self, init_path: str) -> dict[str, object]:
        return {
            "version": self.VERSION,
            "os_version": self.os.VERSION,
            "init": init_path,
            "cpu_count": len(self.machine.cpus),
            "memory_size": len(self.machine.cpu.memory),
        }

    def _restore_boot_manifest(self) -> dict[str, object] | None:
        raw = self.machine.storage.objects.get(self.BOOT_OBJECT)
        if raw is None:
            self.boot_manifest = None
            return None
        manifest = json.loads(raw.decode("utf-8"))
        if manifest.get("version") != self.VERSION:
            raise ValueError("unsupported Coreless boot manifest version")
        self.boot_manifest = manifest
        return manifest

    def _save_boot_manifest(self, init_path: str) -> None:
        self.boot_manifest = self._boot_manifest(init_path)
        self.machine.storage.put(
            self.BOOT_OBJECT,
            json.dumps(
                self.boot_manifest,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            sync=False,
        )

    def boot(self, init_path: str = "/init"):
        """Power on/resume the complete Coreless operating environment."""
        self._save_boot_manifest(init_path)
        self.os.boot()
        self.ai.save()
        self.machine.save_state()
        return self

    def run(self, max_steps: int = 100000) -> int:
        """Run ready Coreless processes through the digital execution engine."""
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        if not self.machine.booted:
            self.boot()

        remaining = max_steps
        total = 0
        while remaining > 0:
            ready = [
                p for p in self.os.processes.processes.values()
                if p.state == "ready"
            ]
            if not ready:
                break
            process = ready[0]
            result = self.os.processes.start(process.pid, remaining)
            used = max(1, result.ticks)
            total += min(used, remaining)
            remaining -= used
            if result.state == "ready" and used >= remaining + used:
                break
        self.ai.save()
        self.machine.save_state()
        return total

    def command(self, line: str) -> str:
        """Execute one command through the native Coreless shell."""
        if not self.machine.booted:
            self.boot()
        return self.os.command(line)

    def checkpoint(self, name: str = "machine") -> str:
        self.ai.save()
        self.machine.save_state()
        return self.machine.checkpoint(name)

    def ai_analyze(self, prompt: str, *, actor: str = "human", context=None, model_ids=None):
        """Run persistent local AI analysis and retain the complete session history."""
        return self.ai.analyze(
            prompt,
            actor=actor,
            context=context,
            model_ids=model_ids,
        )

    def restore(self, name: str = "machine"):
        self.machine.restore_checkpoint(name)
        self.os.restore_state(
            json.loads(self.machine.storage.objects["machine/os"].decode("utf-8"))
        ) if "machine/os" in self.machine.storage.objects else None
        self.ai.restore()
        self._restore_boot_manifest()
        return self

    def shutdown(self):
        self.machine.save_state()
        return self.machine.shutdown()

    def status(self) -> dict[str, object]:
        status = self.os.status()
        status["system_version"] = self.VERSION
        status["boot_manifest"] = self.boot_manifest
        status["ai"] = self.ai.status()
        return status
