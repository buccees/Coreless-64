import sys

import pytest

sys.path.insert(0, ".")
from components import ComponentDescriptor, CorelessComponent, CorelessHub
from component_autodiscovery import ComponentAutoDiscoveryService
from host_device_bridge import (
    HostDeviceBridge,
    HostDeviceDescriptor,
    ReferenceHostDeviceProvider,
)


def component(component_id, role, capabilities=(), model=None, functions=()):
    return CorelessComponent(ComponentDescriptor(
        component_id=component_id,
        role=role,
        capabilities=frozenset(capabilities),
        ai_model_id=model,
        ai_functions=frozenset(functions),
    ))


def test_declared_hardware_role_maps_to_os_device_class_not_a_task():
    gpu = component("video-0", "video-card", {"display.scanout"}, "graphics-model", {"render_frame"})
    descriptor = HostDeviceDescriptor.from_component(gpu)
    assert descriptor.device_class == "display.graphics"
    assert descriptor.ai_model_id == "graphics-model"
    assert descriptor.ai_functions == frozenset({"render_frame"})


def test_network_capability_maps_to_network_device_when_role_is_specific_enough():
    network = component("net-0", "network-adapter", {"network.packet"})
    assert HostDeviceDescriptor.from_component(network).device_class == "network.adapter"


def test_unknown_role_fails_closed_instead_of_becoming_generic_task():
    unknown = component("mystery-0", "do-stuff", {"custom.action"})
    with pytest.raises(ValueError, match="no host device-class mapping"):
        HostDeviceDescriptor.from_component(unknown)


def test_bridge_exposes_each_component_once_and_removes_detached_components():
    provider = ReferenceHostDeviceProvider()
    bridge = HostDeviceBridge(provider)
    net = component("net-0", "network-adapter", {"network.packet"})
    gpu = component("gpu-0", "video-card", {"display.scanout"})

    first = bridge.reconcile([net, gpu])
    second = bridge.reconcile([net, gpu])
    assert all(result.exposed for result in first)
    assert all(result.detail == "already exposed" for result in second)
    assert provider.devices["net-0"][0].device_class == "network.adapter"
    bridge.reconcile([gpu])
    assert "net-0" not in provider.devices
    assert "gpu-0" in provider.devices


def test_discovery_service_syncs_host_device_bridge_after_auto_attach(tmp_path):
    mount = tmp_path / "mounted"
    mount.mkdir()
    manifest = component("network-part", "network-adapter", {"network.packet"})
    (mount / "network.coreless.json").write_bytes(manifest.export_portable_manifest())
    from component_autodiscovery import DirectoryComponentDiscoveryProvider

    hub = CorelessHub("host-device-test")
    provider = ReferenceHostDeviceProvider()
    bridge = HostDeviceBridge(provider)
    service = ComponentAutoDiscoveryService(
        hub, DirectoryComponentDiscoveryProvider([mount]), device_bridge=bridge
    )
    attached = service.scan_once()
    assert len(attached) == 1
    assert provider.devices["network-part"][0].device_class == "network.adapter"


def test_close_unregisters_all_exposed_devices():
    provider = ReferenceHostDeviceProvider()
    bridge = HostDeviceBridge(provider)
    bridge.reconcile([component("net-0", "network-adapter", {"network.packet"})])
    bridge.close()
    assert provider.devices == {}


def test_linux_tap_backend_creates_and_removes_kernel_interface_without_external_device(
    monkeypatch,
):
    import struct
    import host_device_bridge as bridge_module
    from host_device_bridge import LinuxTapHandle, LinuxTapHostDeviceProvider

    opened = []
    closed = []
    calls = []

    def fake_open(path, flags):
        opened.append((path, flags))
        return 73

    def fake_ioctl(fd, request, buffer, mutate_flag):
        calls.append((fd, request, mutate_flag))
        # Simulate the kernel returning the selected interface name in ifreq.
        buffer[:16] = b"cl64abcdef12\0\0\0\0"
        return 0

    monkeypatch.setattr(bridge_module, "sys_platform_linux", lambda: True)
    monkeypatch.setattr(bridge_module.os, "open", fake_open)
    monkeypatch.setattr(bridge_module.os, "close", closed.append)
    monkeypatch.setattr(bridge_module.fcntl, "ioctl", fake_ioctl)

    provider = LinuxTapHostDeviceProvider()
    descriptor = HostDeviceDescriptor.from_component(
        component("network-part", "network-adapter", {"network.packet"})
    )
    handle = provider.expose(descriptor, object())
    assert isinstance(handle, LinuxTapHandle)
    assert handle.interface_name == "cl64abcdef12"
    assert opened[0][0] == "/dev/net/tun"
    assert calls[0][0] == 73
    assert calls[0][2] is True
    provider.remove(handle)
    assert closed == [73]


def test_linux_tap_backend_rejects_non_network_device_classes():
    from host_device_bridge import LinuxTapHostDeviceProvider

    provider = LinuxTapHostDeviceProvider()
    descriptor = HostDeviceDescriptor(
        component_id="video-0",
        device_class="display.graphics",
        role="video-card",
        capabilities=frozenset({"display.scanout"}),
        ai_model_id=None,
        ai_functions=frozenset(),
    )
    with pytest.raises(NotImplementedError, match="display.graphics"):
        provider.expose(descriptor, object())
