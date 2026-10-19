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
from ai.model_part import ComponentRole, HardwareAssignmentRegistry, RoleContract


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
        self.machine.attach_ai_registry(self.ai.registry)
        self.motherboard = self.machine.motherboard
        self.ai_chipset = self.machine.ai_chipset
        self.hardware_assignments = HardwareAssignmentRegistry()
        self._restore_hardware_assignments()
        self._restore_boot_manifest()

    HARDWARE_ASSIGNMENTS_OBJECT = "ai/hardware-assignments"

    def _restore_hardware_assignments(self) -> None:
        raw = self.machine.storage.objects.get(self.HARDWARE_ASSIGNMENTS_OBJECT)
        if raw is None:
            return
        state = json.loads(raw.decode("utf-8"))
        if not isinstance(state, dict) or state.get("version") != 1:
            raise ValueError("unsupported AI hardware-assignment state version")
        entries = state.get("assignments")
        if not isinstance(entries, list):
            raise ValueError("AI hardware-assignment state has invalid assignments")
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("AI hardware-assignment state contains an invalid entry")
            role_data = item.get("role_contract")
            if not isinstance(role_data, dict):
                raise ValueError("AI hardware-assignment state has invalid role contract")
            role = RoleContract(
                role=ComponentRole(role_data["role"]),
                mandatory_capabilities=tuple(role_data.get("mandatory_capabilities", ())),
                retained_optional_capabilities=tuple(role_data.get("retained_optional_capabilities", ())),
                removable_capabilities=tuple(role_data.get("removable_capabilities", ())),
                user_communication=bool(role_data.get("user_communication", False)),
            )
            model_id = item["model_id"]
            self.ai.registry.descriptor(model_id)
            assignment = self.hardware_assignments.assign(
                model_id,
                item["part_id"],
                role,
                native_architecture=item["native_architecture"],
            )
            assignment.validate(tuple(item.get("available_capabilities", ())))

    def assign_ai_hardware_role(
        self,
        model_id: str,
        part_id: str,
        role_contract: RoleContract,
        *,
        native_architecture: str,
        available_capabilities,
    ):
        """Persist a validated model-to-role designation; does not claim live execution binding."""
        self.ai.registry.descriptor(model_id)
        available = tuple(available_capabilities)
        required = set(role_contract.mandatory_capabilities) | set(
            role_contract.retained_optional_capabilities
        )
        missing = required - set(available)
        if missing:
            raise ValueError(
                f"model {model_id} cannot be assigned to {role_contract.role.value}: "
                f"missing {sorted(missing)}"
            )
        assignment = self.hardware_assignments.assign(
            model_id,
            part_id,
            role_contract,
            native_architecture=native_architecture,
        )
        state = {
            "version": 1,
            "assignments": [
                {
                    "model_id": item.model_id,
                    "part_id": item.part_id,
                    "native_architecture": item.native_architecture,
                    "available_capabilities": list(available),
                    "role_contract": {
                        "role": item.role_contract.role.value,
                        "mandatory_capabilities": list(item.role_contract.mandatory_capabilities),
                        "retained_optional_capabilities": list(item.role_contract.retained_optional_capabilities),
                        "removable_capabilities": list(item.role_contract.removable_capabilities),
                        "user_communication": item.role_contract.user_communication,
                    },
                }
                for item in self.hardware_assignments.all()
            ],
        }
        self.machine.storage.put(
            self.HARDWARE_ASSIGNMENTS_OBJECT,
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            sync=False,
        )
        self.machine.save_state()
        return assignment

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
        """Boot Coreless with a modeled active-low motherboard reset cycle."""
        self.motherboard.set_reset(True)
        try:
            self._save_boot_manifest(init_path)
            self.os.boot()
            self.ai.save()
            self.machine.save_state()
        except Exception:
            # Keep reset asserted if the software boot sequence fails.
            raise
        self.motherboard.set_reset(False)
        return self

    def gpio_mode(self, index: int, mode, pull="none") -> None:
        """Configure one virtual Arduino GPIO pin on the motherboard netlist."""
        self.motherboard.set_gpio_mode(index, mode, pull)

    def gpio_write(self, index: int, level: int) -> None:
        """Drive a virtual GPIO signal through the motherboard wire model."""
        self.motherboard.digital_write(index, level)

    def gpio_read(self, index: int) -> int:
        """Read a Coreless-side GPIO pin after digital net resolution."""
        return self.motherboard.digital_read(index)

    def set_external_interrupt(self, asserted: bool) -> None:
        """Drive or release the modeled motherboard interrupt input."""
        self.motherboard.set_interrupt(asserted)

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

    def ai_compute(self, prompt: str, *, model_id: str, actor: str = "human", context=None, operation: str = "ai.infer"):
        """Execute one persistent AI workload through the native machine scheduler."""
        return self.ai.compute(
            self.machine,
            prompt,
            model_id=model_id,
            actor=actor,
            context=context,
            operation=operation,
        )
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
        status["motherboard"] = self.motherboard.snapshot()
        status["ai"] = self.ai.status()
        status["ai_chipset"] = self.ai_chipset.snapshot()
        status["ai_hardware_assignments"] = tuple({
            "model_id": item.model_id,
            "part_id": item.part_id,
            "role": item.role_contract.role.value,
            "native_architecture": item.native_architecture,
            "required_capabilities": item.required_capabilities,
            "retained_optional_capabilities": item.retained_optional_capabilities,
        } for item in self.hardware_assignments.all())
        status["ai"]["machine_resources"] = tuple(
            resource_id
            for resource_id in self.machine.scheduler.resources()
            if resource_id.startswith("ai:")
        )
        return status
