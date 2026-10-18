"""Deterministic digital-circuit reference model for a virtual Coreless board.

This models logical nets, GPIO direction, pull resistors, and conflicting output
drivers. It is a software netlist simulator, not an analog/SPICE model and not
evidence of physical-board behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CircuitError(RuntimeError):
    """Base class for invalid or electrically conflicting circuit operations."""


class FloatingSignalError(CircuitError):
    """Raised when an input has no driven or pulled logical level."""


class ShortCircuitError(CircuitError):
    """Raised when one logical net has conflicting active output drivers."""


class PinMode(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class Pull(str, Enum):
    NONE = "none"
    UP = "up"
    DOWN = "down"


@dataclass
class Pin:
    name: str
    net: str
    mode: PinMode = PinMode.INPUT
    pull: Pull = Pull.NONE
    drive: int | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.net:
            raise ValueError("pin and net names must be non-empty")
        self.mode = PinMode(self.mode)
        self.pull = Pull(self.pull)
        if self.drive not in (None, 0, 1):
            raise ValueError("digital output drive must be 0, 1, or None")
        if self.mode is PinMode.INPUT and self.drive is not None:
            raise ValueError("input pins cannot actively drive a net")


class CircuitBoard:
    """Small deterministic netlist simulator for motherboard/GPIO logic."""

    def __init__(self, name: str = "coreless-board") -> None:
        if not name:
            raise ValueError("board name must be non-empty")
        self.name = name
        self.pins: dict[str, Pin] = {}
        self._parent: dict[str, str] = {}
        self._rails: dict[str, int] = {}

    def define_net(self, name: str) -> None:
        if not name:
            raise ValueError("net name must be non-empty")
        self._parent.setdefault(name, name)

    def _root(self, net: str) -> str:
        if net not in self._parent:
            self.define_net(net)
        parent = self._parent[net]
        if parent != net:
            self._parent[net] = self._root(parent)
        return self._parent[net]

    def add_pin(
        self,
        name: str,
        net: str,
        mode: PinMode | str = PinMode.INPUT,
        pull: Pull | str = Pull.NONE,
    ) -> Pin:
        if name in self.pins:
            raise ValueError(f"duplicate pin: {name}")
        self.define_net(net)
        pin = Pin(name=name, net=net, mode=PinMode(mode), pull=Pull(pull))
        self.pins[name] = pin
        return pin

    def connect(self, *net_names: str) -> None:
        """Join two or more named nets as if linked by ideal wires."""
        if len(net_names) < 2:
            raise ValueError("connect requires at least two nets")
        roots = [self._root(name) for name in net_names]
        canonical = roots[0]
        for root in roots[1:]:
            if root != canonical:
                self._parent[root] = canonical

    def connect_pins(self, *pin_names: str) -> None:
        """Join the nets carrying the named pins, modeling board wiring."""
        if len(pin_names) < 2:
            raise ValueError("connect_pins requires at least two pins")
        missing = [name for name in pin_names if name not in self.pins]
        if missing:
            raise KeyError(f"unknown pin(s): {', '.join(missing)}")
        self.connect(*(self.pins[name].net for name in pin_names))

    def set_rail(self, net: str, level: int) -> None:
        """Attach a fixed logical 0/1 source to a net (e.g. ground or logic rail)."""
        if level not in (0, 1):
            raise ValueError("rail level must be 0 or 1")
        root = self._root(net)
        self._rails[root] = level

    def configure_pin(
        self,
        name: str,
        mode: PinMode | str,
        pull: Pull | str = Pull.NONE,
    ) -> None:
        pin = self._pin(name)
        pin.mode = PinMode(mode)
        pin.pull = Pull(pull)
        if pin.mode is PinMode.INPUT:
            pin.drive = None

    def write(self, name: str, level: int) -> None:
        pin = self._pin(name)
        if pin.mode is not PinMode.OUTPUT:
            raise CircuitError(f"cannot write to input pin: {name}")
        if level not in (0, 1):
            raise ValueError("digital output level must be 0 or 1")
        pin.drive = level
        # Resolve now so an output conflict is reported at the write site.
        self.read(name)

    def release(self, name: str) -> None:
        """Put an output into high impedance; it no longer drives the net."""
        pin = self._pin(name)
        if pin.mode is not PinMode.OUTPUT:
            raise CircuitError(f"only output pins can be released: {name}")
        pin.drive = None

    def read(self, name: str) -> int:
        pin = self._pin(name)
        root = self._root(pin.net)
        drivers = {
            other.drive
            for other in self.pins.values()
            if self._root(other.net) == root
            and other.mode is PinMode.OUTPUT
            and other.drive is not None
        }
        if root in self._rails:
            drivers.add(self._rails[root])
        if len(drivers) > 1:
            raise ShortCircuitError(f"conflicting logic drivers on net {root}")
        if drivers:
            return next(iter(drivers))
        pulls = {
            1 if other.pull is Pull.UP else 0
            for other in self.pins.values()
            if self._root(other.net) == root and other.mode is PinMode.INPUT
            and other.pull is not Pull.NONE
        }
        if len(pulls) > 1:
            raise ShortCircuitError(f"conflicting pull resistors on net {root}")
        if pulls:
            return next(iter(pulls))
        raise FloatingSignalError(f"undriven input on net {root}")

    def continuity(self, first_net: str, second_net: str) -> bool:
        """Return whether two named net labels are electrically connected."""
        return self._root(first_net) == self._root(second_net)

    def snapshot(self) -> dict[str, object]:
        """Return a stable, JSON-friendly diagnostic snapshot."""
        return {
            "board": self.name,
            "pins": {
                name: {
                    "net": self._root(pin.net),
                    "mode": pin.mode.value,
                    "pull": pin.pull.value,
                    "drive": pin.drive,
                }
                for name, pin in sorted(self.pins.items())
            },
        }

    def _pin(self, name: str) -> Pin:
        try:
            return self.pins[name]
        except KeyError as exc:
            raise KeyError(f"unknown pin: {name}") from exc
