"""Shared regional ship movement and hull-damage rules.

This is a deterministic campaign-layer model: ships move through shared
world coordinates using per-turn movement allowances. Tactical engagements
can then advance on a separate real-time tick without resetting positions.
It is a game abstraction, not a naval-performance simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Iterable


class RegionalWorldError(ValueError):
    """Raised when a movement or damage action is invalid."""


@dataclass
class RegionalShip:
    ship_id: str
    name: str
    x: float
    y: float
    speed: float
    max_hull: int
    hull: int | None = None
    weapon_damage: int = 1
    movement_spent: float = 0.0
    damage_by_system: dict[str, int] = field(default_factory=dict)
    sunk: bool = False

    def __post_init__(self) -> None:
        if not self.ship_id or not self.name:
            raise RegionalWorldError("ship id and name are required")
        if self.speed <= 0:
            raise RegionalWorldError("speed must be positive")
        if self.max_hull <= 0:
            raise RegionalWorldError("max_hull must be positive")
        if self.weapon_damage <= 0:
            raise RegionalWorldError("weapon_damage must be positive")
        if self.hull is None:
            self.hull = self.max_hull
        if not 0 <= self.hull <= self.max_hull:
            raise RegionalWorldError("hull must be between zero and max_hull")
        self.sunk = self.hull == 0

    @property
    def movement_remaining(self) -> float:
        return max(0.0, self.speed - self.movement_spent)

    @property
    def afloat(self) -> bool:
        return not self.sunk and self.hull > 0


@dataclass(frozen=True)
class MovementResult:
    ship_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    distance: float
    movement_remaining: float


@dataclass(frozen=True)
class DamageResult:
    target_id: str
    damage: int
    hull_before: int
    hull_after: int
    sunk: bool
    system: str


class RegionalWorld:
    """Authoritative campaign map state with turn-based movement allowances."""

    def __init__(self, ships: Iterable[RegionalShip] = ()) -> None:
        self.ships: dict[str, RegionalShip] = {}
        self.turn = 1
        for ship in ships:
            self.add_ship(ship)

    def add_ship(self, ship: RegionalShip) -> None:
        if ship.ship_id in self.ships:
            raise RegionalWorldError(f"duplicate ship id: {ship.ship_id}")
        self.ships[ship.ship_id] = ship

    def move(self, ship_id: str, x: float, y: float) -> MovementResult:
        ship = self._ship(ship_id)
        if not ship.afloat:
            raise RegionalWorldError("a sunk ship cannot move")
        if not all(isinstance(v, (int, float)) for v in (x, y)):
            raise RegionalWorldError("destination coordinates must be numeric")
        distance = hypot(float(x) - ship.x, float(y) - ship.y)
        # Tiny tolerance avoids rejecting a destination due to float rounding.
        if distance > ship.movement_remaining + 1e-9:
            raise RegionalWorldError("destination exceeds this ship's remaining movement")
        start = (ship.x, ship.y)
        ship.x, ship.y = float(x), float(y)
        ship.movement_spent = min(ship.speed, ship.movement_spent + distance)
        return MovementResult(
            ship_id=ship.ship_id,
            start=start,
            end=(ship.x, ship.y),
            distance=distance,
            movement_remaining=ship.movement_remaining,
        )

    def apply_hit(
        self, target_id: str, damage: int | None = None, *, system: str = "hull"
    ) -> DamageResult:
        target = self._ship(target_id)
        if not target.afloat:
            raise RegionalWorldError("target is already sunk")
        if damage is None:
            raise RegionalWorldError("damage must be supplied by the resolved weapon hit")
        if type(damage) is not int or damage <= 0:
            raise RegionalWorldError("damage must be a positive integer")
        if not system or system not in {"hull", "propulsion", "sensors", "weapons", "flooding"}:
            raise RegionalWorldError("unknown damage system")
        before = int(target.hull or 0)
        target.hull = max(0, before - damage)
        target.damage_by_system[system] = target.damage_by_system.get(system, 0) + damage
        target.sunk = target.hull == 0
        return DamageResult(
            target_id=target.ship_id,
            damage=damage,
            hull_before=before,
            hull_after=target.hull,
            sunk=target.sunk,
            system=system,
        )

    def end_turn(self) -> int:
        """Advance campaign turn and refresh each afloat ship's movement allowance."""
        self.turn += 1
        for ship in self.ships.values():
            ship.movement_spent = 0.0
        return self.turn

    def public_map(self, visible_ship_ids: set[str]) -> list[dict[str, object]]:
        """Return only caller-authorized ship observations; no hidden ships leak."""
        return [
            {
                "ship_id": ship.ship_id,
                "name": ship.name,
                "x": ship.x,
                "y": ship.y,
                "afloat": ship.afloat,
            }
            for ship in self.ships.values()
            if ship.ship_id in visible_ship_ids
        ]

    def _ship(self, ship_id: str) -> RegionalShip:
        try:
            return self.ships[ship_id]
        except KeyError as exc:
            raise RegionalWorldError("unknown ship") from exc
