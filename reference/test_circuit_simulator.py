import pytest

from circuit_simulator import (
    CircuitBoard,
    CircuitError,
    FloatingSignalError,
    PinMode,
    Pull,
    ShortCircuitError,
)


def make_board():
    board = CircuitBoard("virtual-motherboard")
    board.add_pin("mcu.out", "data", PinMode.OUTPUT)
    board.add_pin("mcu.in", "data", PinMode.INPUT)
    return board


def test_output_wire_drives_input_high_and_low():
    board = make_board()
    board.write("mcu.out", 1)
    assert board.read("mcu.in") == 1
    board.write("mcu.out", 0)
    assert board.read("mcu.in") == 0


def test_floating_input_is_not_silently_treated_as_low():
    board = make_board()
    with pytest.raises(FloatingSignalError, match="undriven input"):
        board.read("mcu.in")


def test_pull_up_and_pull_down_resolve_idle_input():
    board = CircuitBoard()
    board.add_pin("button", "button-net", pull=Pull.UP)
    assert board.read("button") == 1
    board.configure_pin("button", PinMode.INPUT, Pull.DOWN)
    assert board.read("button") == 0


def test_conflicting_output_drivers_report_short_circuit():
    board = CircuitBoard()
    board.add_pin("driver.high", "shared", PinMode.OUTPUT)
    board.add_pin("driver.low", "shared", PinMode.OUTPUT)
    board.write("driver.high", 1)
    with pytest.raises(ShortCircuitError, match="conflicting logic drivers"):
        board.write("driver.low", 0)


def test_fixed_rail_conflict_is_detected():
    board = CircuitBoard()
    board.add_pin("gpio", "rail", PinMode.OUTPUT)
    board.set_rail("rail", 0)
    with pytest.raises(ShortCircuitError):
        board.write("gpio", 1)


def test_wire_connects_separate_nets_and_continuity_is_reported():
    board = CircuitBoard()
    board.add_pin("gpio", "gpio-net", PinMode.OUTPUT)
    board.add_pin("device.in", "device-net", PinMode.INPUT)
    assert not board.continuity("gpio-net", "device-net")
    board.connect_pins("gpio", "device.in")
    assert board.continuity("gpio-net", "device-net")
    board.write("gpio", 1)
    assert board.read("device.in") == 1


def test_released_output_becomes_high_impedance():
    board = make_board()
    board.write("mcu.out", 1)
    board.release("mcu.out")
    with pytest.raises(FloatingSignalError):
        board.read("mcu.in")


def test_input_pin_cannot_be_written_and_duplicate_pins_are_rejected():
    board = make_board()
    with pytest.raises(CircuitError, match="cannot write to input"):
        board.write("mcu.in", 1)
    with pytest.raises(ValueError, match="duplicate pin"):
        board.add_pin("mcu.in", "other")


def test_fixed_rail_follows_wire_and_conflicting_rails_cannot_be_joined():
    board = CircuitBoard()
    board.add_pin("gpio", "gpio-net", PinMode.OUTPUT)
    board.add_pin("ground", "ground-net", PinMode.INPUT)
    board.set_rail("ground-net", 0)
    board.connect_pins("gpio", "ground")
    with pytest.raises(ShortCircuitError):
        board.write("gpio", 1)

    other = CircuitBoard()
    other.set_rail("ground", 0)
    other.set_rail("vcc", 1)
    with pytest.raises(ShortCircuitError, match="conflicting fixed rails"):
        other.connect("ground", "vcc")
