"""Shared regional ship movement and hull-damage rules.

This is a deterministic campaign-layer model: ships move through shared
world coordinates using per-turn movement allowances. Tactical engagements
can then advance on a separate real-time tick without resetting positions.
It is a game abstraction, not a naval-performance simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, hypot, isfinite, radians, sin
from typing import Iterable


class RegionalWorldError(ValueError):
    """Raised when a movement or damage action is invalid."""


# Game-balance starting values: one ship occupies one map/board location.
# With one damage per successful hit, these values are hits-to-sink.
SHIP_CLASS_HULL = {
    "patrol": 3,
    "corvette": 4,
    "submarine": 4,
    "frigate": 5,
    "destroyer": 6,
    "cruiser": 8,
    "battleship": 10,
    "carrier": 12,
}


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
    weapon_range: float = 0.15
    movement_spent: float = 0.0
    damage_by_system: dict[str, int] = field(default_factory=dict)
    sunk: bool = False
    ship_class: str = "custom"
    length_m: float | None = None
    beam_m: float | None = None
    blueprint_source: str | None = None
    heading_deg: float = 0.0
    faction_id: str | None = None

    @classmethod
    def from_class(
        cls, *, ship_id: str, name: str, ship_class: str, x: float, y: float,
        speed: float, weapon_damage: int = 1, weapon_range: float = 0.15,
        faction_id: str | None = None
    ) -> "RegionalShip":
        """Create a ship whose hull points are determined by its class."""
        key = ship_class.strip().lower()
        if key not in SHIP_CLASS_HULL:
            raise RegionalWorldError(f"unknown ship class: {ship_class}")
        return cls(
            ship_id=ship_id, name=name, x=x, y=y, speed=speed,
            max_hull=SHIP_CLASS_HULL[key], weapon_damage=weapon_damage,
            weapon_range=weapon_range, ship_class=key, faction_id=faction_id,
        )

    @classmethod
    def from_blueprint(
        cls, *, ship_id: str, name: str, ship_class: str, x: float, y: float,
        speed: float, length_m: float, beam_m: float, blueprint_source: str,
        max_hull: int, weapon_damage: int = 1, weapon_range: float = 0.15,
        heading_deg: float = 0.0, faction_id: str | None = None
    ) -> "RegionalShip":
        """Create a dimensioned ship from a cited blueprint/specification source.

        Dimensions are real-world metres; map rendering must preserve length:beam
        ratio rather than stretching each ship to fit a generic icon.
        """
        if length_m <= 0 or beam_m <= 0 or length_m < beam_m:
            raise RegionalWorldError("ship dimensions must be positive and length >= beam")
        if not blueprint_source or not blueprint_source.strip():
            raise RegionalWorldError("blueprint_source is required for sourced ship geometry")
        if not 0 <= heading_deg < 360:
            raise RegionalWorldError("heading_deg must be in [0, 360)")
        return cls(
            ship_id=ship_id, name=name, x=x, y=y, speed=speed,
            max_hull=max_hull, weapon_damage=weapon_damage, weapon_range=weapon_range,
            ship_class=ship_class, length_m=length_m, beam_m=beam_m,
            blueprint_source=blueprint_source.strip(), heading_deg=heading_deg,
            faction_id=faction_id,
        )

    @property
    def aspect_ratio(self) -> float | None:
        """True plan-view length-to-beam ratio; None until sourced dimensions exist."""
        if self.length_m is None or self.beam_m is None:
            return None
        return self.length_m / self.beam_m

    @property
    def hits_to_sink_at_one_damage(self) -> int:
        """Number of additional one-point hits needed to sink this ship."""
        return int(self.hull or 0)

    def __post_init__(self) -> None:
        if not self.ship_id or not self.name:
            raise RegionalWorldError("ship id and name are required")
        if self.speed <= 0:
            raise RegionalWorldError("speed must be positive")
        if self.max_hull <= 0:
            raise RegionalWorldError("max_hull must be positive")
        if self.weapon_damage <= 0:
            raise RegionalWorldError("weapon_damage must be positive")
        if not isinstance(self.weapon_range, (int, float)) or not isfinite(self.weapon_range) or self.weapon_range <= 0:
            raise RegionalWorldError("weapon_range must be a finite positive number")
        if self.hull is None:
            self.hull = self.max_hull
        if not 0 <= self.hull <= self.max_hull:
            raise RegionalWorldError("hull must be between zero and max_hull")
        self.sunk = self.hull == 0
        if (self.length_m is None) != (self.beam_m is None):
            raise RegionalWorldError("length and beam must be supplied together")
        if self.length_m is not None and (
            self.length_m <= 0 or self.beam_m is None or self.beam_m <= 0 or self.length_m < self.beam_m
        ):
            raise RegionalWorldError("ship dimensions must be positive and length >= beam")
        if not 0 <= self.heading_deg < 360:
            raise RegionalWorldError("heading_deg must be in [0, 360)")

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

    def advance_realtime_tick(self, delta_seconds: float) -> list[MovementResult]:
        """Advance all afloat ships together for a fixed real-time interval.

        Speed is world-coordinate units per second. Heading is degrees clockwise
        from north (0=north, 90=east). This is separate from campaign movement
        allowances, so real-time ticks do not spend the campaign movement budget.
        """
        if not isinstance(delta_seconds, (int, float)) or not isfinite(delta_seconds) or delta_seconds <= 0:
            raise RegionalWorldError("delta_seconds must be a finite positive number")
        results: list[MovementResult] = []
        for ship in self.ships.values():
            if not ship.afloat:
                continue
            start = (ship.x, ship.y)
            distance = ship.speed * float(delta_seconds)
            angle = radians(ship.heading_deg)
            ship.x += sin(angle) * distance
            ship.y += cos(angle) * distance
            results.append(MovementResult(
                ship_id=ship.ship_id, start=start, end=(ship.x, ship.y),
                distance=distance, movement_remaining=ship.movement_remaining,
            ))
        return results

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
                "faction_id": ship.faction_id,
                "name": ship.name,
                "x": ship.x,
                "y": ship.y,
                "afloat": ship.afloat,
                "hull": ship.hull,
                "max_hull": ship.max_hull,
                "ship_class": ship.ship_class,
                "length_m": ship.length_m,
                "beam_m": ship.beam_m,
                "aspect_ratio": ship.aspect_ratio,
                "heading_deg": ship.heading_deg,
                "speed": ship.speed,
                "weapon_range": ship.weapon_range,
                "blueprint_source": ship.blueprint_source,
            }
            for ship in self.ships.values()
            if ship.ship_id in visible_ship_ids
        ]

    def public_snapshot(
        self, visible_ship_ids: set[str], *,
        world_bounds: tuple[float, float, float, float] | None = None,
    ) -> dict[str, object]:
        """Return a versioned browser/API snapshot of authorized observations.

        ``world_bounds`` is (min_x, min_y, max_x, max_y). When supplied, the
        snapshot includes normalized map positions only for ships inside bounds.
        Without bounds, only already-normalized world coordinates in [0, 1] are
        mapped. Hidden ships are never included.
        """
        if world_bounds is not None:
            min_x, min_y, max_x, max_y = world_bounds
            if not all(isfinite(v) for v in world_bounds) or max_x <= min_x or max_y <= min_y:
                raise RegionalWorldError("world_bounds must be finite with positive width and height")
        ships = []
        for item in self.public_map(visible_ship_ids):
            x, y = float(item["x"]), float(item["y"])
            if world_bounds is None:
                if not (0 <= x <= 1 and 0 <= y <= 1):
                    continue
                normalized = [x, y]
            else:
                if not (min_x <= x <= max_x and min_y <= y <= max_y):
                    continue
                normalized = [(x - min_x) / (max_x - min_x), (y - min_y) / (max_y - min_y)]
            item["normalized_position"] = normalized
            ships.append(item)
        return {"schema_version": 1, "turn": self.turn, "ships": ships}
    def _ship(self, ship_id: str) -> RegionalShip:
        try:
            return self.ships[ship_id]
        except KeyError as exc:
            raise RegionalWorldError("unknown ship") from exc
