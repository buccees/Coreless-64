"""Canonical digital-only motherboard wiring for the Coreless reference computer.

The topology explicitly connects virtual Arduino GPIO to Coreless-side pins using
CircuitBoard nets. This is a logical netlist, not a claim of analog, timing,
current, thermal, or physical hardware equivalence.
"""
from __future__ import annotations

from circuit_simulator import CircuitBoard, PinMode, Pull


class VirtualGPIOPeripheral:
    """Minimal digital peripheral contract: GPIO level controls an attached LED."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.level: int | None = None
        self.energized = False
        self.transitions: list[int] = []

    def drive(self, level: int) -> None:
        if level not in (0, 1):
            raise ValueError("peripheral level must be 0 or 1")
        if self.level != level:
            self.transitions.append(level)
        self.level = level
        self.energized = level == 1

    def snapshot(self) -> dict[str, object]:
        return {
            "name": self.name,
            "level": self.level,
            "energized": self.energized,
            "transitions": list(self.transitions),
        }


class VirtualMotherboard:
    """A deterministic digital motherboard netlist with virtual Arduino I/O."""

    GPIO_COUNT = 4

    def __init__(self) -> None:
        self.board = CircuitBoard("coreless-virtual-motherboard")
        board = self.board

        # Fixed logical rails. They represent named digital states, not voltages.
        board.add_pin("rail.vcc", "VCC")
        board.add_pin("rail.gnd", "GND")
        board.set_rail("VCC", 1)
        board.set_rail("GND", 0)

        # Reset is active-low and idles high through a modeled pull-up.
        board.add_pin("core.reset_n", "CORE_RESET_N", PinMode.INPUT, Pull.UP)
        board.add_pin("arduino.reset_n", "ARDUINO_RESET_N", PinMode.OUTPUT)
        board.connect_pins("core.reset_n", "arduino.reset_n")

        # Clock source and Coreless clock input are explicitly wired.
        board.add_pin("arduino.clock", "ARDUINO_CLOCK", PinMode.OUTPUT)
        board.add_pin("core.clock", "CORE_CLOCK", PinMode.INPUT)
        board.connect_pins("arduino.clock", "core.clock")
        board.write("arduino.clock", 0)

        # Shared interrupt line; the Arduino side can assert or release it.
        board.add_pin("arduino.irq", "ARDUINO_IRQ", PinMode.OUTPUT)
        board.add_pin("core.irq", "CORE_IRQ", PinMode.INPUT, Pull.DOWN)
        board.connect_pins("arduino.irq", "core.irq")
        board.release("arduino.irq")

        # GPIO lines are physically separate net labels joined by explicit wires.
        for index in range(self.GPIO_COUNT):
            arduino_pin = f"arduino.D{index}"
            core_pin = f"core.gpio{index}"
            board.add_pin(arduino_pin, f"ARDUINO_D{index}", PinMode.INPUT)
            board.add_pin(core_pin, f"CORE_GPIO{index}", PinMode.INPUT)
            board.connect_pins(arduino_pin, core_pin)

        board.write("arduino.reset_n", 1)
        self._clock_level = 0
        # GPIO0 is wired to a modeled status LED; the remaining pins are
        # available for future explicitly specified peripheral contracts.
        self.peripherals = {"status_led": VirtualGPIOPeripheral("status_led")}

    def set_gpio_mode(self, index: int, mode: PinMode | str, pull: Pull | str = Pull.NONE) -> None:
        self._check_gpio(index)
        self.board.configure_pin(f"arduino.D{index}", mode, pull)

    def digital_write(self, index: int, level: int) -> None:
        self._check_gpio(index)
        self.board.write(f"arduino.D{index}", level)
        if index == 0:
            # Resolve through the netlist before notifying the peripheral.
            self.peripherals["status_led"].drive(self.board.read("core.gpio0"))

    def digital_read(self, index: int) -> int:
        self._check_gpio(index)
        return self.board.read(f"core.gpio{index}")

    def set_reset(self, asserted: bool) -> None:
        """Assert active-low reset when True; deassert it when False."""
        self.board.write("arduino.reset_n", 0 if asserted else 1)

    @property
    def reset_asserted(self) -> bool:
        return self.board.read("core.reset_n") == 0

    def clock_tick(self) -> int:
        """Advance one modeled digital clock edge and return the resulting level."""
        self._clock_level = 1 - self._clock_level
        self.board.write("arduino.clock", self._clock_level)
        return self.board.read("core.clock")

    def set_interrupt(self, asserted: bool) -> None:
        if asserted:
            self.board.configure_pin("arduino.irq", PinMode.OUTPUT)
            self.board.write("arduino.irq", 1)
        else:
            self.board.release("arduino.irq")

    @property
    def interrupt_asserted(self) -> bool:
        return self.board.read("core.irq") == 1

    def continuity_report(self) -> dict[str, bool]:
        """Report required logical wire joins in the canonical netlist."""
        pairs = {
            "reset": ("CORE_RESET_N", "ARDUINO_RESET_N"),
            "clock": ("CORE_CLOCK", "ARDUINO_CLOCK"),
            "interrupt": ("CORE_IRQ", "ARDUINO_IRQ"),
        }
        pairs.update({
            f"gpio{index}": (f"CORE_GPIO{index}", f"ARDUINO_D{index}")
            for index in range(self.GPIO_COUNT)
        })
        return {
            name: self.board.continuity(left, right)
            for name, (left, right) in pairs.items()
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "board": self.board.snapshot(),
            "continuity": self.continuity_report(),
            "reset_asserted": self.reset_asserted,
            "interrupt_asserted": self.interrupt_asserted,
            "peripherals": {
                name: peripheral.snapshot()
                for name, peripheral in self.peripherals.items()
            },
        }

    def _check_gpio(self, index: int) -> None:
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < self.GPIO_COUNT:
            raise ValueError(f"GPIO index must be between 0 and {self.GPIO_COUNT - 1}")
