"""Host-facing virtual-device bridge for automatically recognized Coreless parts.

This bridge maps a component's declared hardware role to an OS device class.
It does not infer a role from arbitrary files and never converts a component
into a generic task. A platform provider is responsible for registering a real
OS-visible virtual device (for example, through a Linux kernel/device API).
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import os
import struct
from typing import Iterable, Protocol


@dataclass(frozen=True)
class HostDeviceDescriptor:
    """OS-facing device identity derived from a Coreless component contract."""

    component_id: str
    device_class: str
    role: str
    capabilities: frozenset[str]
    ai_model_id: str | None
    ai_functions: frozenset[str]

    @classmethod
    def from_component(cls, component: object) -> "HostDeviceDescriptor":
        descriptor = getattr(component, "descriptor", None)
        if descriptor is None:
            raise TypeError("Coreless component has no descriptor")
        role = str(getattr(descriptor, "role", "")).strip().lower()
        capabilities = frozenset(getattr(descriptor, "capabilities", ()))
        device_class = _device_class(role, capabilities)
        if device_class is None:
            raise ValueError(
                f"component role {role!r} has no host device-class mapping; "
                "declare a supported hardware role instead of assigning a task"
            )
        component_id = getattr(descriptor, "component_id", None)
        if not isinstance(component_id, str) or not component_id:
            raise ValueError("component identity is missing")
        return cls(
            component_id=component_id,
            device_class=device_class,
            role=role,
            capabilities=capabilities,
            ai_model_id=getattr(descriptor, "ai_model_id", None),
            ai_functions=frozenset(getattr(descriptor, "ai_functions", ())),
        )


# Roles are architectural hardware identities, not workload/task names.
_ROLE_CLASSES = {
    "cpu": "coreless.cpu",
    "coreless-cpu": "coreless.cpu",
    "graphics": "display.graphics",
    "video-card": "display.graphics",
    "gpu": "display.graphics",
    "graphics-card": "display.graphics",
    "network": "network.adapter",
    "network-adapter": "network.adapter",
    "communication-input": "communication.interface",
    "input": "input.controller",
    "input-controller": "input.controller",
    "storage": "storage.controller",
    "storage-controller": "storage.controller",
    "ai-chipset": "coreless.ai-chipset",
    "chipset": "coreless.ai-chipset",
    "reasoning-planning": "coreless.reasoning",
    "code-firmware": "coreless.code-firmware",
}


def _device_class(role: str, capabilities: frozenset[str]) -> str | None:
    if role in _ROLE_CLASSES:
        return _ROLE_CLASSES[role]
    # Capability fallback is intentionally narrow and deterministic.
    prefixes = (
        ("network.", "network.adapter"),
        ("display.", "display.graphics"),
        ("graphics.", "display.graphics"),
        ("input.", "input.controller"),
        ("storage.", "storage.controller"),
    )
    for prefix, device_class in prefixes:
        if any(item.startswith(prefix) for item in capabilities):
            return device_class
    return None


class HostDeviceProvider(Protocol):
    """Platform boundary that exposes and removes OS-visible virtual devices."""

    def expose(self, descriptor: HostDeviceDescriptor, component: object) -> object:
        """Register a virtual device with the host OS and return its opaque handle."""
        ...

    def remove(self, handle: object) -> None:
        """Unregister a previously exposed virtual device."""
        ...


@dataclass(frozen=True)
class DeviceExposure:
    component_id: str
    device_class: str
    exposed: bool
    detail: str = ""


class HostDeviceBridge:
    """Keep host-visible device registration synchronized with Hub components.

    A successful bridge result means the supplied platform provider accepted
    registration. It is not evidence of physical hardware or a kernel driver
    unless that provider actually implements and verifies those facilities.
    """

    def __init__(self, provider: HostDeviceProvider) -> None:
        if not callable(getattr(provider, "expose", None)) or not callable(
            getattr(provider, "remove", None)
        ):
            raise TypeError("host device provider must implement expose() and remove()")
        self.provider = provider
        self._handles: dict[str, tuple[HostDeviceDescriptor, object]] = {}

    def reconcile(self, components: Iterable[object]) -> tuple[DeviceExposure, ...]:
        live: dict[str, object] = {}
        for component in components:
            descriptor = getattr(component, "descriptor", None)
            component_id = getattr(descriptor, "component_id", None)
            if isinstance(component_id, str) and component_id:
                live[component_id] = component

        results: list[DeviceExposure] = []
        for component_id in sorted(set(self._handles) - set(live)):
            _, handle = self._handles.pop(component_id)
            self.provider.remove(handle)

        for component_id, component in sorted(live.items()):
            if not getattr(component, "healthy", True):
                results.append(DeviceExposure(component_id, "unknown", False, "component is fault-isolated"))
                continue
            try:
                descriptor = HostDeviceDescriptor.from_component(component)
                existing = self._handles.get(component_id)
                if existing is not None and existing[0] == descriptor:
                    results.append(DeviceExposure(component_id, descriptor.device_class, True, "already exposed"))
                    continue
                if existing is not None:
                    # Replace transactionally: preserve the existing device if
                    # the new role cannot be exposed.
                    new_handle = self.provider.expose(descriptor, component)
                    old_handle = existing[1]
                    self._handles[component_id] = (descriptor, new_handle)
                    self.provider.remove(old_handle)
                else:
                    handle = self.provider.expose(descriptor, component)
                    self._handles[component_id] = (descriptor, handle)
                results.append(DeviceExposure(component_id, descriptor.device_class, True, "registered"))
            except Exception as exc:
                descriptor = getattr(component, "descriptor", None)
                role = str(getattr(descriptor, "role", "unknown"))
                results.append(DeviceExposure(component_id, role, False, str(exc)))
        return tuple(results)

    def close(self) -> None:
        """Remove every device registered by this bridge."""
        errors: list[Exception] = []
        for component_id in sorted(tuple(self._handles)):
            _, handle = self._handles.pop(component_id)
            try:
                self.provider.remove(handle)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError(f"failed to remove {len(errors)} host virtual device(s)") from errors[0]


class ReferenceHostDeviceProvider:
    """In-memory provider for deterministic tests; it does not register OS devices."""

    def __init__(self) -> None:
        self.devices: dict[str, tuple[HostDeviceDescriptor, object]] = {}

    def expose(self, descriptor: HostDeviceDescriptor, component: object) -> str:
        existing = self.devices.get(descriptor.component_id)
        if existing is not None and existing[0] != descriptor:
            raise ValueError("component identity is already exposed with a different device class")
        handle = f"reference-host-device:{descriptor.component_id}"
        self.devices[descriptor.component_id] = (descriptor, component)
        return handle

    def remove(self, handle: object) -> None:
        prefix = "reference-host-device:"
        if not isinstance(handle, str) or not handle.startswith(prefix):
            raise ValueError("unknown reference host-device handle")
        self.devices.pop(handle[len(prefix):], None)



@dataclass(frozen=True)
class LinuxTapHandle:
    """Open Linux TAP endpoint; closing its descriptor removes the transient link."""

    component_id: str
    interface_name: str
    file_descriptor: int


class LinuxTapHostDeviceProvider:
    """Expose network-adapter components as Linux kernel TAP interfaces.

    Requires Linux, /dev/net/tun, and permission to create TAP interfaces
    (normally CAP_NET_ADMIN/root). This backend creates an OS-visible network
    interface only; packet forwarding into the Coreless network controller is a
    separate data-plane integration and is intentionally not faked here.
    """

    TUNSETIFF = 0x400454CA
    IFF_TAP = 0x0002
    IFF_NO_PI = 0x1000

    def expose(self, descriptor: HostDeviceDescriptor, component: object) -> LinuxTapHandle:
        if not sys_platform_linux():
            raise OSError("Linux TAP backend is supported only on Linux")
        if descriptor.device_class != "network.adapter":
            raise NotImplementedError(
                f"Linux host-device backend does not yet implement {descriptor.device_class!r}"
            )
        digest = hashlib.sha256(descriptor.component_id.encode("utf-8")).hexdigest()[:8]
        interface_name = f"cl64{digest}"[:15]
        fd = os.open("/dev/net/tun", os.O_RDWR)
        try:
            request = bytearray(struct.pack("16sH", interface_name.encode("ascii"), self.IFF_TAP | self.IFF_NO_PI))
            fcntl.ioctl(fd, self.TUNSETIFF, request, True)
            actual_name = struct.unpack("16sH", request[:18])[0].split(bytes((0,)), 1)[0].decode("ascii")
            return LinuxTapHandle(descriptor.component_id, actual_name, fd)
        except Exception:
            os.close(fd)
            raise

    def remove(self, handle: object) -> None:
        if not isinstance(handle, LinuxTapHandle):
            raise TypeError("Linux TAP provider received an invalid device handle")
        os.close(handle.file_descriptor)


def sys_platform_linux() -> bool:
    """Isolated platform check, kept patchable for backend contract tests."""
    import sys
    return sys.platform.startswith("linux")
