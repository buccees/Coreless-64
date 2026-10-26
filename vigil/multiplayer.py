"""Authoritative, player-isolated Battleship room state for future network transport.

This module is the game/session core only. It is not a public server by itself;
a deployment must expose it through authenticated HTTPS endpoints.
"""
from __future__ import annotations

import secrets
import string
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable

BOARD_SIZE = 10
SHIP_LENGTHS = (5, 4, 3, 3, 2)
ROOM_TTL_SECONDS = 2 * 60 * 60
ROOM_ALPHABET = string.ascii_uppercase + string.digits


class MultiplayerError(ValueError):
    """A rejected room, fleet, turn, or shot operation."""


def _cell(value: object) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise MultiplayerError("each fleet cell must be [row, column]")
    row, col = value
    if type(row) is not int or type(col) is not int:
        raise MultiplayerError("cell coordinates must be integers")
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        raise MultiplayerError("cell is outside the board")
    return row, col


def _validate_fleet(fleet: object) -> tuple[frozenset[tuple[int, int]], ...]:
    if not isinstance(fleet, (list, tuple)) or len(fleet) != len(SHIP_LENGTHS):
        raise MultiplayerError("fleet must contain five ships of lengths 5, 4, 3, 3, and 2")
    ships = []
    occupied: set[tuple[int, int]] = set()
    for raw_ship, expected_length in zip(fleet, SHIP_LENGTHS):
        if not isinstance(raw_ship, (list, tuple)) or len(raw_ship) != expected_length:
            raise MultiplayerError("ship lengths must be 5, 4, 3, 3, and 2 in that order")
        cells = tuple(_cell(cell) for cell in raw_ship)
        if len(set(cells)) != expected_length or occupied.intersection(cells):
            raise MultiplayerError("fleet ships may not overlap")
        rows = {r for r, _ in cells}
        cols = {c for _, c in cells}
        if len(rows) != 1 and len(cols) != 1:
            raise MultiplayerError("each ship must be straight")
        ordered = sorted(r for r, _ in cells) if len(rows) == 1 else sorted(c for _, c in cells)
        if ordered != list(range(ordered[0], ordered[0] + expected_length)):
            raise MultiplayerError("ship cells must be contiguous")
        occupied.update(cells)
        ships.append(frozenset(cells))
    return tuple(ships)


@dataclass
class _Player:
    token: str
    fleet: tuple[frozenset[tuple[int, int]], ...]
    shots: dict[tuple[int, int], bool] = field(default_factory=dict)


@dataclass
class _Room:
    code: str
    created_at: float
    players: dict[int, _Player | None] = field(default_factory=lambda: {1: None, 2: None})
    turn: int = 1
    winner: int | None = None


class BattleshipRooms:
    """In-memory authoritative rooms; each bearer token sees only its own view."""

    def __init__(self, *, ttl_seconds: int = ROOM_TTL_SECONDS) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl = ttl_seconds
        self._rooms: dict[str, _Room] = {}
        self._token_index: dict[str, tuple[str, int]] = {}
        self._lock = threading.RLock()

    def _prune(self, now: float) -> None:
        expired = [code for code, room in self._rooms.items() if now - room.created_at >= self._ttl]
        for code in expired:
            room = self._rooms.pop(code)
            for player in room.players.values():
                if player is not None:
                    self._token_index.pop(player.token, None)

    def _new_code(self) -> str:
        for _ in range(100):
            code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
            if code not in self._rooms:
                return code
        raise RuntimeError("could not allocate a unique room code")

    def create_room(self, fleet: object) -> dict[str, str]:
        checked = _validate_fleet(fleet)
        with self._lock:
            self._prune(time.monotonic())
            code = self._new_code()
            token = secrets.token_urlsafe(32)
            room = _Room(code=code, created_at=time.monotonic())
            room.players[1] = _Player(token=token, fleet=checked)
            self._rooms[code] = room
            self._token_index[token] = (code, 1)
            return {"room_code": code, "player_token": token}

    def join_room(self, room_code: str, fleet: object) -> dict[str, str]:
        checked = _validate_fleet(fleet)
        if not isinstance(room_code, str):
            raise MultiplayerError("invalid room code")
        code = room_code.strip().upper()
        with self._lock:
            self._prune(time.monotonic())
            room = self._rooms.get(code)
            if room is None:
                raise MultiplayerError("room not found or expired")
            if room.players[2] is not None:
                raise MultiplayerError("room already has two players")
            token = secrets.token_urlsafe(32)
            room.players[2] = _Player(token=token, fleet=checked)
            self._token_index[token] = (code, 2)
            return {"room_code": code, "player_token": token}

    def _resolve(self, token: str) -> tuple[_Room, int, _Player]:
        if not isinstance(token, str) or not token:
            raise MultiplayerError("invalid player token")
        self._prune(time.monotonic())
        location = self._token_index.get(token)
        if location is None:
            raise MultiplayerError("session not found or expired")
        room_code, player_number = location
        room = self._rooms[room_code]
        player = room.players[player_number]
        if player is None or not secrets.compare_digest(player.token, token):
            raise MultiplayerError("session not found or expired")
        return room, player_number, player

    @staticmethod
    def _view(room: _Room, number: int, player: _Player) -> dict:
        opponent = room.players[2 if number == 1 else 1]
        incoming = []
        if opponent is not None:
            incoming = [
                {"row": row, "column": col}
                for row, col in sorted(opponent.shots)
            ]
        return {
            "room_code": room.code,
            "player": number,
            "player_count": sum(p is not None for p in room.players.values()),
            "ready": all(p is not None for p in room.players.values()),
            "turn": room.turn if room.winner is None else None,
            "winner": room.winner,
            "game_over": room.winner is not None,
            "own_fleet": [
                [{"row": r, "column": c} for r, c in sorted(ship)]
                for ship in player.fleet
            ],
            "outgoing_shots": [
                {"row": row, "column": col, "hit": hit}
                for (row, col), hit in sorted(player.shots.items())
            ],
            "incoming_shots": incoming,
        }

    def view(self, player_token: str) -> dict:
        with self._lock:
            room, number, player = self._resolve(player_token)
            return self._view(room, number, player)

    def fire(self, player_token: str, row: int, column: int) -> dict:
        cell = _cell([row, column])
        with self._lock:
            room, number, player = self._resolve(player_token)
            if room.winner is not None:
                raise MultiplayerError("game is over")
            if room.players[1] is None or room.players[2] is None:
                raise MultiplayerError("waiting for the second player")
            if room.turn != number:
                raise MultiplayerError("not your turn")
            if cell in player.shots:
                raise MultiplayerError("cell has already been targeted")
            opponent = room.players[2 if number == 1 else 1]
            assert opponent is not None
            hit = any(cell in ship for ship in opponent.fleet)
            player.shots[cell] = hit
            if all(
                all(target in player.shots and player.shots[target] for target in ship)
                for ship in opponent.fleet
            ):
                room.winner = number
            else:
                room.turn = 2 if number == 1 else 1
            return self._view(room, number, player)
