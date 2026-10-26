"""Authoritative regional game-session foundation for VIGIL.

This layer owns player authorization, accepted commands, and simulation ticks.
It intentionally does not pretend to implement weapons, sensors, persistence,
network transport, or a continuously running production server yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from threading import RLock
from typing import Iterable, Mapping

from .regional_world import RegionalWorld, RegionalWorldError


class RegionalGameError(ValueError):
    """Raised when a session, player, or command is invalid."""


@dataclass(frozen=True)
class PlayerSession:
    player_id: str
    token: str
    controlled_ship_ids: frozenset[str]
    visible_ship_ids: frozenset[str]


class RegionalGame:
    """Shared authoritative state for single-player, AI, and multiplayer clients.

    The same validated command path is used regardless of whether a caller is a
    human client or an AI policy. Tokens are opaque bearer credentials; a network
    server must transport them securely and must not log them.
    """

    def __init__(
        self,
        world: RegionalWorld,
        *,
        world_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        self.world = world
        self.world_bounds = world_bounds
        self.simulation_tick = 0
        self._sessions_by_token: dict[str, PlayerSession] = {}
        self._tokens_by_player: dict[str, str] = {}
        self._lock = RLock()

    def register_player(
        self,
        *,
        player_id: str,
        token: str,
        controlled_ship_ids: Iterable[str],
        visible_ship_ids: Iterable[str] | None = None,
    ) -> PlayerSession:
        """Register a player with explicit ship control and observation grants."""
        if not isinstance(player_id, str) or not player_id.strip():
            raise RegionalGameError("player_id is required")
        if not isinstance(token, str) or not token.strip():
            raise RegionalGameError("token is required")
        controlled = frozenset(controlled_ship_ids)
        visible = frozenset(visible_ship_ids if visible_ship_ids is not None else controlled)
        if not controlled:
            raise RegionalGameError("at least one controlled ship is required")
        if not visible.issuperset(controlled):
            raise RegionalGameError("players must be able to observe their controlled ships")
        with self._lock:
            if token in self._sessions_by_token:
                raise RegionalGameError("token is already registered")
            if player_id in self._tokens_by_player:
                raise RegionalGameError("player_id is already registered")
            missing = (controlled | visible).difference(self.world.ships)
            if missing:
                raise RegionalGameError("session references an unknown ship")
            session = PlayerSession(player_id, token, controlled, visible)
            self._sessions_by_token[token] = session
            self._tokens_by_player[player_id] = token
            return session

    def session_for_token(self, token: str) -> PlayerSession:
        """Resolve a bearer token without disclosing whether a player ID exists."""
        with self._lock:
            session = self._sessions_by_token.get(token)
            if session is None:
                raise RegionalGameError("unauthorized")
            return session

    def snapshot(self, token: str) -> dict[str, object]:
        """Return only the observations granted to this session."""
        with self._lock:
            session = self.session_for_token(token)
            snapshot = self.world.public_snapshot(
                set(session.visible_ship_ids), world_bounds=self.world_bounds
            )
            snapshot["simulation_tick"] = self.simulation_tick
            snapshot["player_id"] = session.player_id
            snapshot["controlled_ship_ids"] = sorted(session.controlled_ship_ids)
            return snapshot

    def command(self, token: str, operation: str, arguments: Mapping[str, object]) -> dict[str, object]:
        """Validate and apply a supported player command through one authority path."""
        if not isinstance(arguments, Mapping):
            raise RegionalGameError("command arguments must be an object")
        with self._lock:
            session = self.session_for_token(token)
            ship_id = arguments.get("ship_id")
            if operation in {"set_heading", "campaign_move"}:
                if not isinstance(ship_id, str) or ship_id not in session.controlled_ship_ids:
                    raise RegionalGameError("player does not control that ship")
                ship = self.world.ships[ship_id]
                if not ship.afloat:
                    raise RegionalGameError("a sunk ship cannot receive commands")

                if operation == "set_heading":
                    heading = arguments.get("heading_deg")
                    if (isinstance(heading, bool) or not isinstance(heading, (int, float))
                            or not isfinite(heading) or not 0 <= heading < 360):
                        raise RegionalGameError("heading_deg must be finite and in [0, 360)")
                    ship.heading_deg = float(heading)
                    return {
                        "ok": True, "operation": operation, "ship_id": ship_id,
                        "heading_deg": ship.heading_deg,
                    }

                x, y = arguments.get("x"), arguments.get("y")
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                       for v in (x, y)):
                    raise RegionalGameError("destination coordinates must be finite numbers")
                result = self.world.move(ship_id, float(x), float(y))
                return {
                    "ok": True, "operation": operation, "ship_id": ship_id,
                    "position": [result.end[0], result.end[1]],
                    "movement_remaining": result.movement_remaining,
                }

            if operation == "end_campaign_turn":
                if session.player_id != "host":
                    raise RegionalGameError("only the host may advance the campaign turn")
                turn = self.world.end_turn()
                return {"ok": True, "operation": operation, "turn": turn}

            raise RegionalGameError("unsupported command")

    def advance_tick(self, delta_seconds: float) -> dict[str, object]:
        """Advance the shared simulation once; caller owns the wall-clock loop."""
        with self._lock:
            movements = self.world.advance_realtime_tick(delta_seconds)
            self.simulation_tick += 1
            return {
                "simulation_tick": self.simulation_tick,
                "delta_seconds": float(delta_seconds),
                "moved_ship_ids": [movement.ship_id for movement in movements],
            }
