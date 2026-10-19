import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from component_autodiscovery import (
    ComponentAutoDiscoveryService,
    DirectoryComponentDiscoveryProvider,
    LinuxMountedComponentDiscoveryProvider,
)
from components import ComponentDescriptor, CorelessComponent, CorelessHub


def write_manifest(path: Path, component_id: str, model_id: str | None = None) -> None:
    component = CorelessComponent(ComponentDescriptor(
        component_id=component_id,
        role="communication-input",
        capabilities=frozenset({"network.message"}),
        ai_model_id=model_id,
        ai_functions=frozenset({"communication_response"}) if model_id else frozenset(),
    ))
    path.write_bytes(component.export_portable_manifest())


def test_directory_provider_automatically_recognizes_manifest_on_mounted_media(tmp_path):
    mount = tmp_path / "removable-drive"
    mount.mkdir()
    provider = DirectoryComponentDiscoveryProvider([mount])
    assert provider.enumerate_candidates() == ()

    write_manifest(mount / "communication.coreless.json", "communication-peripheral", "gemma")
    candidates = provider.enumerate_candidates()

    assert len(candidates) == 1
    assert candidates[0].endpoint_id.endswith("communication.coreless.json")
    payload = json.loads(candidates[0].manifest.decode("utf-8"))
    assert payload["descriptor"]["component_id"] == "communication-peripheral"


def test_directory_provider_recognizes_package_layout_and_ignores_symlinks(tmp_path):
    mount = tmp_path / "mounted"
    mount.mkdir()
    package = mount / "storage-peripheral"
    package.mkdir()
    write_manifest(package / "component.json", "storage-peripheral")
    outside = tmp_path / "outside.coreless.json"
    write_manifest(outside, "outside")
    (mount / "linked.coreless.json").symlink_to(outside)

    candidates = DirectoryComponentDiscoveryProvider([mount]).enumerate_candidates()
    assert len(candidates) == 1
    assert json.loads(candidates[0].manifest)["descriptor"]["component_id"] == "storage-peripheral"


def test_hub_discovery_auto_attaches_new_component_and_is_idempotent(tmp_path):
    mount = tmp_path / "usb-mount"
    mount.mkdir()
    manifest_path = mount / "display.coreless.json"
    write_manifest(manifest_path, "display-peripheral")
    provider = DirectoryComponentDiscoveryProvider([mount])
    hub = CorelessHub("auto-recognition-hub")

    first = hub.discover_and_attach(provider)
    second = hub.discover_and_attach(provider)

    assert len(first) == 1
    assert second == first
    assert hub.component("display-peripheral") is first[0]
    assert first[0].hub_id == "auto-recognition-hub"


def test_auto_discovery_service_picks_up_component_added_after_start(tmp_path):
    mount = tmp_path / "hot-mounted-drive"
    mount.mkdir()
    provider = DirectoryComponentDiscoveryProvider([mount])
    hub = CorelessHub("polling-discovery-hub")
    errors = []
    service = ComponentAutoDiscoveryService(
        hub, provider, interval=0.02, on_error=errors.append
    )
    service.start()
    try:
        write_manifest(mount / "network.coreless.json", "network-peripheral")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not hub.components():
            time.sleep(0.01)
        assert hub.component("network-peripheral").hub_id == "polling-discovery-hub"
        assert errors == []
    finally:
        service.stop()


def test_discovery_rejects_conflicting_component_identity(tmp_path):
    mount = tmp_path / "two-devices"
    mount.mkdir()
    write_manifest(mount / "first.coreless.json", "same-id")
    write_manifest(mount / "second.coreless.json", "same-id", "gemma")
    provider = DirectoryComponentDiscoveryProvider([mount])

    with pytest.raises(ValueError, match="conflicting portable manifests"):
        provider.enumerate_candidates()



def test_linux_mount_provider_picks_up_newly_mounted_component_volume(tmp_path):
    volume = tmp_path / "mounted-ssd"
    volume.mkdir()
    mount_table = tmp_path / "mounts"
    provider = LinuxMountedComponentDiscoveryProvider(
        mount_table=mount_table,
        install_roots=(),
    )

    mount_table.write_text(f"/dev/fake {volume} ext4 rw,relatime 0 0\n")
    assert provider.enumerate_candidates() == ()

    write_manifest(volume / "network.coreless.json", "mounted-network")
    candidates = provider.enumerate_candidates()
    assert len(candidates) == 1
    assert json.loads(candidates[0].manifest)["descriptor"]["component_id"] == "mounted-network"


def test_linux_mount_provider_unescapes_mountpoint_spaces(tmp_path):
    volume = tmp_path / "ssd with spaces"
    volume.mkdir()
    mount_table = tmp_path / "mounts"
    escaped = str(volume).replace(" ", "\\040")
    mount_table.write_text(f"/dev/fake {escaped} ext4 rw 0 0\n")
    write_manifest(volume / "storage.coreless.json", "mounted-storage")

    provider = LinuxMountedComponentDiscoveryProvider(
        mount_table=mount_table,
        install_roots=(),
    )
    assert [json.loads(item.manifest)["descriptor"]["component_id"]
            for item in provider.enumerate_candidates()] == ["mounted-storage"]
