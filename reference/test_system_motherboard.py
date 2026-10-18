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

def test_system_and_machine_share_one_authoritative_motherboard():
    system = CorelessSystem()
    assert system.motherboard is system.machine.motherboard


def test_machine_execution_is_gated_by_motherboard_reset():
    system = CorelessSystem()
    machine = system.machine
    machine.boot()
    calls = []
    machine.cpu.step = lambda: calls.append("step") or True
    machine.motherboard.set_reset(True)

    assert machine.run(3) == 0
    assert calls == []

    machine.motherboard.set_reset(False)
    assert machine.run(2) == 2
    assert calls == ["step", "step"]
    assert machine.motherboard.board.read("core.clock") == 0


def test_motherboard_interrupt_reaches_existing_cpu_pending_interrupts():
    system = CorelessSystem()
    machine = system.machine
    machine.boot()
    machine.cpu.step = lambda: True
    system.set_external_interrupt(True)

    assert machine.run(1) == 1
    assert machine.cpu.pending_interrupts & (1 << 2)

    system.set_external_interrupt(False)
    assert machine.motherboard.interrupt_asserted is False
