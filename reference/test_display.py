import sys
sys.path.insert(0, ".")
from machine_runtime import CorelessMachine
from os_runtime import CorelessOS


def test_status_led_tray_dot_opens_live_menu():
    machine = CorelessMachine(4096)
    os = CorelessOS(machine)
    desktop = os.desktop

    assert desktop.tray_items() == [
        {"id": "status_led", "kind": "dot", "anchor": "battery", "label": "GPIO0 status LED"}
    ]
    assert desktop.tray_menu is None
    initial = desktop.open_tray_menu()
    assert initial["state"] == "UNDRIVEN"
    assert initial["transitions"] == []

    machine.motherboard.set_gpio_mode(0, "output")
    machine.motherboard.digital_write(0, 1)
    on = desktop.status_led_menu()
    assert on["state"] == "ON"
    assert on["energized"] is True
    assert on["transitions"] == [1]

    machine.motherboard.digital_write(0, 0)
    off = desktop.status_led_menu()
    assert off["state"] == "OFF"
    assert off["energized"] is False
    assert off["transitions"] == [1, 0]


def test_status_led_tray_menu_is_transient_and_saved():
    machine = CorelessMachine(4096)
    desktop = CorelessOS(machine).desktop
    desktop.open_tray_menu()
    state = desktop.save_state()
    restored_machine = CorelessMachine(4096)
    restored = CorelessOS(restored_machine).desktop
    restored.restore_state(state)
    assert restored.tray_menu == "status_led"
    restored.close_tray_menu()
    assert restored.tray_menu is None
