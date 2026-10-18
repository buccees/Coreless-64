import sys
from pathlib import Path

REFERENCE = Path(__file__).parent
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import run_desktop
from system import CorelessSystem


def test_desktop_launcher_boots_and_persists_selected_image(tmp_path, monkeypatch):
    image = tmp_path / "installed-coreless.json"
    opened = {}

    class FakeDesktopHost:
        def __init__(self, desktop):
            opened["desktop"] = desktop

        def run(self):
            opened["ran"] = True

    monkeypatch.setattr(run_desktop, "TkDesktopHost", FakeDesktopHost)

    assert run_desktop.main([str(image), "--memory", "65536"]) == 0
    assert opened["ran"] is True

    # Reopen the exact image passed to the launcher. The launcher must not
    # have created an unrelated in-memory machine or a second storage target.
    reopened = CorelessSystem(memory_size=65536, storage_path=image)
    assert reopened.machine.booted is True
    assert reopened.machine.power_state == "on"
    assert reopened.os.desktop is not None
    assert opened["desktop"] is not None


def test_desktop_launcher_requires_explicit_image():
    import pytest

    with pytest.raises(SystemExit) as exc:
        run_desktop.main([])
    assert exc.value.code == 2
