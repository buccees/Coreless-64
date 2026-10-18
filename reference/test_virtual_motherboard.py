import pytest

from circuit_simulator import CircuitError, FloatingSignalError, PinMode
from virtual_motherboard import VirtualMotherboard


def test_canonical_motherboard_explicitly_wires_all_required_nets():
    motherboard = VirtualMotherboard()

    assert motherboard.continuity_report() == {
        "reset": True,
        "clock": True,
        "interrupt": True,
        "gpio0": True,
        "gpio1": True,
        "gpio2": True,
        "gpio3": True,
    }


def test_virtual_arduino_gpio_drives_coreless_side_through_wire_model():
    motherboard = VirtualMotherboard()
    motherboard.set_gpio_mode(0, PinMode.OUTPUT)
    motherboard.digital_write(0, 1)
    assert motherboard.digital_read(0) == 1
    motherboard.digital_write(0, 0)
    assert motherboard.digital_read(0) == 0


def test_gpio_input_without_driver_or_pull_is_reported_as_floating():
    motherboard = VirtualMotherboard()
    with pytest.raises(FloatingSignalError):
        motherboard.digital_read(0)


def test_gpio_rejects_invalid_pin_numbers_and_output_to_input_writes():
    motherboard = VirtualMotherboard()
    with pytest.raises(ValueError, match="GPIO index"):
        motherboard.digital_write(99, 1)
    with pytest.raises(CircuitError, match="cannot write to input"):
        motherboard.digital_write(1, 1)


def test_active_low_reset_is_connected_and_tracks_assertion():
    motherboard = VirtualMotherboard()
    assert motherboard.reset_asserted is False
    motherboard.set_reset(True)
    assert motherboard.reset_asserted is True
    motherboard.set_reset(False)
    assert motherboard.reset_asserted is False


def test_clock_edges_propagate_to_coreless_clock_input():
    motherboard = VirtualMotherboard()
    assert motherboard.board.read("core.clock") == 0
    assert motherboard.clock_tick() == 1
    assert motherboard.clock_tick() == 0


def test_interrupt_assert_and_release_propagate_with_pull_down_idle():
    motherboard = VirtualMotherboard()
    assert motherboard.interrupt_asserted is False
    motherboard.set_interrupt(True)
    assert motherboard.interrupt_asserted is True
    motherboard.set_interrupt(False)
    assert motherboard.interrupt_asserted is False


def test_power_rails_have_distinct_logical_levels():
    motherboard = VirtualMotherboard()
    assert motherboard.board.read("rail.vcc") == 1
    assert motherboard.board.read("rail.gnd") == 0


def test_snapshot_includes_wiring_and_line_state():
    snapshot = VirtualMotherboard().snapshot()
    assert snapshot["board"]["board"] == "coreless-virtual-motherboard"
    assert all(snapshot["continuity"].values())
    assert snapshot["reset_asserted"] is False
    assert snapshot["interrupt_asserted"] is False


def test_gpio0_transitions_drive_modeled_status_led_peripheral():
    motherboard = VirtualMotherboard()
    led = motherboard.peripherals["status_led"]
    assert led.level is None
    assert led.energized is False

    motherboard.set_gpio_mode(0, PinMode.OUTPUT)
    motherboard.digital_write(0, 1)
    assert motherboard.digital_read(0) == 1
    assert led.level == 1
    assert led.energized is True

    motherboard.digital_write(0, 1)
    assert led.transitions == [1]
    motherboard.digital_write(0, 0)
    assert led.level == 0
    assert led.energized is False
    assert led.transitions == [1, 0]


def test_motherboard_snapshot_reports_peripheral_state():
    motherboard = VirtualMotherboard()
    motherboard.set_gpio_mode(0, PinMode.OUTPUT)
    motherboard.digital_write(0, 1)
    assert motherboard.snapshot()["peripherals"]["status_led"] == {
        "name": "status_led",
        "level": 1,
        "energized": True,
        "transitions": [1],
    }

