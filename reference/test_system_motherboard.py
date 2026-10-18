import pytest

from circuit_simulator import FloatingSignalError, PinMode
from system import CorelessSystem


def test_coreless_system_exposes_the_motherboard_netlist_in_status():
    system = CorelessSystem()
    motherboard = system.status()["motherboard"]

    assert motherboard["board"]["board"] == "coreless-virtual-motherboard"
    assert all(motherboard["continuity"].values())


def test_coreless_system_gpio_api_uses_motherboard_signal_resolution():
    system = CorelessSystem()
    system.gpio_mode(0, PinMode.OUTPUT)
    system.gpio_write(0, 1)
    assert system.gpio_read(0) == 1
    system.gpio_write(0, 0)
    assert system.gpio_read(0) == 0


def test_coreless_system_boot_cycles_modeled_reset():
    system = CorelessSystem()
    system.boot()
    assert system.motherboard.reset_asserted is False
    assert system.status()["motherboard"]["reset_asserted"] is False


def test_coreless_system_rejects_reading_an_undriven_gpio():
    system = CorelessSystem()
    with pytest.raises(FloatingSignalError):
        system.gpio_read(2)
