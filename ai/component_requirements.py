"""Coreless component requirements envelope.

The envelope describes capabilities a specialized AI component may need to
interoperate with the full computer. It is intentionally broader than any
single model or VM. Specialization may remove unused capabilities only after
the task contract and validation suite prove they are unnecessary.

A deployed part implements the complete requirement profile for its hardware role; it does not need unrelated capabilities.
"""

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping


# Capability families cover the major compute, memory, interconnect, storage,
# networking, media, security, reliability, and external-I/O surfaces expected
# of a modern computer.
COMPUTE = frozenset({
    "scalar_compute", "integer_compute", "floating_point", "vector_compute",
    "matrix_compute", "parallel_compute", "atomic_operations",
    "branch_control", "cryptographic_compute",
})
AI = frozenset({
    "tensor_compute", "attention", "moe_routing", "embedding",
    "quantized_compute", "mixed_precision", "inference", "specialization",
    "model_adaptation",
})
MEMORY = frozenset({
    "virtual_memory", "shared_memory", "persistent_memory",
    "cacheable_memory", "coherent_memory", "dma", "memory_protection",
    "memory_compression",
})
STORAGE = frozenset({
    "block_storage", "nvme", "persistent_storage", "filesystem_io",
    "checkpoint_restore", "storage_encryption", "storage_integrity",
})
INTERCONNECT = frozenset({
    "high_speed_io", "pcie", "cxl_like_coherence", "device_discovery",
    "hotplug", "peer_to_peer_dma", "interrupts", "iommu",
})
NETWORK = frozenset({
    "ethernet", "wifi", "bluetooth", "low_latency_networking",
    "packet_processing", "network_acceleration", "secure_transport",
})
MEDIA = frozenset({
    "display_output", "display_input", "gpu_compute", "graphics",
    "video_encode", "video_decode", "audio_input", "audio_output",
    "camera_input", "image_processing",
})
EXTERNAL_IO = frozenset({
    "usb", "usb4_class_io", "high_speed_external_io", "keyboard",
    "pointer", "touch", "game_controller", "serial_io",
    "generic_peripheral_io",
})
SYSTEM = frozenset({
    "virtualization", "process_isolation", "scheduling", "telemetry",
    "audit", "fault_isolation", "checkpointing", "power_management",
    "thermal_awareness",
})
SECURITY = frozenset({
    "capability_security", "access_control", "secure_boot",
    "attestation", "key_isolation", "sandboxing", "rollback",
    "secure_update",
})
RELIABILITY = frozenset({
    "error_detection", "error_correction", "timeout_recovery",
    "health_monitoring", "deterministic_validation", "redundancy",
})


@dataclass(frozen=True)
class RequirementEnvelope:
    """Hardware-class capability envelope used by specialization planning."""

    name: str
    capabilities: FrozenSet[str]
    version: int = 1

    def contains(self, capability: str) -> bool:
        return capability in self.capabilities

    def missing(self, required: Iterable[str]) -> FrozenSet[str]:
        return frozenset(required) - self.capabilities

    def subset(self, requested: Iterable[str]) -> "RequirementEnvelope":
        requested_set = frozenset(requested)
        return RequirementEnvelope(
            name=f"{self.name}.specialized",
            version=self.version,
            capabilities=self.capabilities & requested_set,
        )


# Broad reference envelope. A component selects a complete role from this
# envelope. Selection defines what the component MUST retain, not a list of
# conveniences that may later be stripped away.
CURRENT_COMPUTER_ENVELOPE = RequirementEnvelope(
    name="coreless.current-computer-io",
    capabilities=frozenset().union(
        COMPUTE, AI, MEMORY, STORAGE, INTERCONNECT, NETWORK,
        MEDIA, EXTERNAL_IO, SYSTEM, SECURITY, RELIABILITY,
    ),
)


@dataclass(frozen=True)
class RequirementProfile:
    """Complete mandatory requirements for one hardware-component role."""

    task_id: str
    required: FrozenSet[str]
    
    def validate_against(self, envelope: RequirementEnvelope) -> None:
        missing = envelope.missing(self.required)
        if missing:
            raise ValueError(
                f"requirements outside envelope: {sorted(missing)}"
            )


def make_profile(
    task_id: str,
    required: Iterable[str],
    *,
    envelope: RequirementEnvelope = CURRENT_COMPUTER_ENVELOPE,
) -> RequirementProfile:
    profile = RequirementProfile(
        task_id=task_id,
        required=frozenset(required),
    )
    profile.validate_against(envelope)
    return profile
