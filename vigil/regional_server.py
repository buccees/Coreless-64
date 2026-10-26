"""TLS development launcher for the VIGIL regional game-session API.

This is a small LAN/smoke-test host, not a production deployment. Production
should use a maintained WSGI server, TLS reverse proxy, durable storage, and a
managed identity/session service. Player tokens are loaded from environment
variables named by the config; do not place bearer tokens in the config file.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import ssl
import threading
from pathlib import Path
from time import monotonic
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from vigil.regional_game import RegionalGame
from vigil.regional_game_http import create_regional_game_app
from vigil.regional_ai import RegionalOpponent, RegionalOpponentRunner
from vigil.regional_world import RegionalShip, RegionalWorld, SHIP_CLASS_HULL


def load_game_config(
    path: str | Path, *, ai_tokens: dict[str, str] | None = None
) -> RegionalGame:
    """Load a version-1 game roster and player grants from a local JSON file."""
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("unable to read valid game config") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("unsupported game config schema_version")
    ship_entries, player_entries = config.get("ships"), config.get("players")
    if not isinstance(ship_entries, list) or not ship_entries:
        raise ValueError("config must contain a non-empty ships list")
    if not isinstance(player_entries, list) or not player_entries:
        raise ValueError("config must contain a non-empty players list")

    ships = []
    for item in ship_entries:
        if not isinstance(item, dict):
            raise ValueError("each ship config must be an object")
        ship_class = item.get("ship_class", "custom")
        if ship_class not in SHIP_CLASS_HULL:
            raise ValueError("each ship must use a supported ship_class")
        heading = item.get("heading_deg", 0.0)
        if isinstance(heading, bool) or not isinstance(heading, (int, float)) or not 0 <= heading < 360:
            raise ValueError("heading_deg must be in [0, 360)")
        dimensions = ("length_m" in item, "beam_m" in item, "blueprint_source" in item)
        if any(dimensions) and not all(dimensions):
            raise ValueError("length_m, beam_m, and blueprint_source must be supplied together")
        common = dict(
            ship_id=item.get("ship_id"), name=item.get("name"),
            ship_class=ship_class, x=item.get("x"), y=item.get("y"),
            speed=item.get("speed"), weapon_damage=item.get("weapon_damage", 1),
            weapon_range=item.get("weapon_range", 0.15),
            faction_id=item.get("faction_id"),
        )
        if all(dimensions):
            ship = RegionalShip.from_blueprint(
                **common, length_m=item["length_m"], beam_m=item["beam_m"],
                blueprint_source=item["blueprint_source"],
                max_hull=item.get("max_hull", SHIP_CLASS_HULL[ship_class]),
                heading_deg=float(heading),
            )
        else:
            ship = RegionalShip.from_class(**common)
            ship.heading_deg = float(heading)
            if "max_hull" in item and item["max_hull"] != ship.max_hull:
                raise ValueError("custom max_hull requires a dimensioned blueprint entry")
        if "hull" in item:
            hull = item["hull"]
            if type(hull) is not int or not 0 <= hull <= ship.max_hull:
                raise ValueError("hull must be an integer between zero and max_hull")
            ship.hull = hull
            ship.sunk = hull == 0
        ships.append(ship)

    world = RegionalWorld(ships)
    bounds = config.get("world_bounds")
    if bounds is not None:
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError("world_bounds must contain four numbers")
        bounds = tuple(bounds)
    game = RegionalGame(world, world_bounds=bounds)
    for item in player_entries:
        if not isinstance(item, dict):
            raise ValueError("each player config must be an object")
        player_id, token_env = item.get("player_id"), item.get("token_env")
        is_ai = item.get("ai", False)
        if type(is_ai) is not bool:
            raise ValueError("player ai flag must be a boolean")
        if is_ai:
            token = secrets.token_urlsafe(32)
        else:
            if not isinstance(token_env, str) or not token_env:
                raise ValueError("each human player must specify token_env")
            token = os.environ.get(token_env)
            if not token:
                raise ValueError(f"required player token environment variable is missing: {token_env}")
        game.register_player(
            player_id=player_id, token=token,
            controlled_ship_ids=item.get("controlled_ship_ids", []),
            visible_ship_ids=item.get("visible_ship_ids"),
        )
        if is_ai and ai_tokens is not None:
            ai_tokens[player_id] = token
    return game


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        # Never log Authorization headers or request bodies.
        print("VIGIL regional API:", fmt % args)


class RegionalTickRunner:
    """Fixed-step background tick loop; slow hosts slow simulation rather than skipping ticks."""

    def __init__(self, game: RegionalGame, tick_rate: float = 10.0) -> None:
        if isinstance(tick_rate, bool) or not isinstance(tick_rate, (int, float)) or not 0.1 <= tick_rate <= 60:
            raise ValueError("tick_rate must be between 0.1 and 60 Hz")
        self.game = game
        self.interval = 1.0 / float(tick_rate)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: Exception | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="vigil-regional-ticks", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        deadline = monotonic() + self.interval
        while not self._stop.wait(max(0.0, deadline - monotonic())):
            try:
                self.game.advance_tick(self.interval)
                self.last_error = None
            except Exception as exc:  # Keep HTTP host alive; expose failure for diagnostics.
                self.last_error = exc
            deadline += self.interval
            # Do not burst through a large backlog after a stalled process.
            if deadline < monotonic() - self.interval:
                deadline = monotonic() + self.interval


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the VIGIL regional game API for development/LAN testing."
    )
    parser.add_argument("--config", required=True, help="version-1 regional game JSON roster")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8445)
    parser.add_argument("--tick-rate", type=float, default=10.0)
    parser.add_argument("--cert", default=os.environ.get("VIGIL_TLS_CERT"))
    parser.add_argument("--key", default=os.environ.get("VIGIL_TLS_KEY"))
    parser.add_argument("--allowed-origin", action="append", default=None)
    args = parser.parse_args()
    origins = args.allowed_origin or [
        value.strip() for value in os.environ.get("VIGIL_REGIONAL_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]
    if not origins:
        parser.error("provide --allowed-origin or VIGIL_REGIONAL_ALLOWED_ORIGINS")
    if not args.cert or not args.key:
        parser.error("TLS is required; provide --cert/--key or VIGIL_TLS_CERT/VIGIL_TLS_KEY")
    try:
        ai_tokens: dict[str, str] = {}
        game = load_game_config(args.config, ai_tokens=ai_tokens)
        ticks = RegionalTickRunner(game, args.tick_rate)
        ai_runner = RegionalOpponentRunner(
            game, {token: RegionalOpponent() for token in ai_tokens.values()}
        )
        app = create_regional_game_app(game=game, allowed_origins=origins)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server = make_server(
        args.host, args.port, app, server_class=WSGIServer, handler_class=QuietHandler
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f"VIGIL regional API listening at https://{args.host}:{args.port}/")
    print(f"Authoritative regional simulation: {args.tick_rate:g} fixed ticks/second.")
    print("Development/LAN only; configure production WSGI, TLS proxy, identity, and persistence separately.")
    if ai_tokens:
        print(f"Started {len(ai_tokens)} AI opponent(s) using deterministic fallback policy.")
    ticks.start()
    ai_runner.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ai_runner.stop()
        ticks.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
