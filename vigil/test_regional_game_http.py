import io
import json

from vigil.regional_game import RegionalGame
from vigil.regional_game_http import create_regional_game_app
from vigil.regional_world import RegionalShip, RegionalWorld


ORIGIN = "https://vigil.example"


def make_app():
    world = RegionalWorld([
        RegionalShip.from_class(
            ship_id="blue", name="Blue Ship", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.01,
        ),
        RegionalShip.from_class(
            ship_id="red", name="Red Ship", ship_class="frigate",
            x=0.8, y=0.7, speed=0.01,
        ),
    ])
    game = RegionalGame(world)
    game.register_player(
        player_id="host", token="host-secret", controlled_ship_ids={"blue"}
    )
    game.register_player(
        player_id="opponent", token="opponent-secret", controlled_ship_ids={"red"}
    )
    return create_regional_game_app(game=game, allowed_origins=[ORIGIN]), game


def request(app, path, method="GET", token="host-secret", origin=ORIGIN, body=None):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_ORIGIN": origin,
        "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
        "CONTENT_LENGTH": str(len(raw)) if method == "POST" else "",
        "wsgi.input": io.BytesIO(raw),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    payload = b"".join(app(environ, start_response))
    captured["body"] = json.loads(payload) if payload else None
    return captured


def test_snapshot_endpoint_returns_only_authorized_ships():
    app, _ = make_app()
    response = request(app, "/api/regional/snapshot")
    assert response["status"] == "200 OK"
    assert [ship["ship_id"] for ship in response["body"]["ships"]] == ["blue"]
    assert "Red Ship" not in repr(response["body"])
    assert response["headers"]["Cache-Control"] == "no-store"
    assert response["headers"]["X-Content-Type-Options"] == "nosniff"


def test_command_endpoint_applies_owned_ship_command():
    app, game = make_app()
    response = request(
        app, "/api/regional/command", method="POST",
        body={"operation": "set_heading", "arguments": {"ship_id": "blue", "heading_deg": 180}},
    )
    assert response["status"] == "200 OK"
    assert response["body"]["heading_deg"] == 180
    assert game.world.ships["blue"].heading_deg == 180


def test_command_endpoint_rejects_cross_player_control():
    app, game = make_app()
    response = request(
        app, "/api/regional/command", method="POST",
        body={"operation": "set_heading", "arguments": {"ship_id": "red", "heading_deg": 180}},
    )
    assert response["status"] == "400 Bad Request"
    assert game.world.ships["red"].heading_deg == 0


def test_auth_and_origin_are_required():
    app, _ = make_app()
    assert request(app, "/api/regional/snapshot", token="bad")["status"] == "401 Unauthorized"
    assert request(app, "/api/regional/snapshot", token="")["status"] == "401 Unauthorized"
    assert request(app, "/api/regional/snapshot", origin="https://evil.example")["status"] == "403 Forbidden"


def test_method_and_json_are_validated():
    app, _ = make_app()
    assert request(app, "/api/regional/snapshot", method="POST", body={})["status"] == "405 Method Not Allowed"
    assert request(app, "/api/regional/command", method="POST", body=[])["status"] == "400 Bad Request"
    assert request(app, "/missing")["status"] == "404 Not Found"


def test_options_preflight_allows_only_documented_methods_and_headers():
    app, _ = make_app()
    response = request(app, "/api/regional/command", method="OPTIONS")
    assert response["status"] == "204 No Content"
    assert response["headers"]["Access-Control-Allow-Origin"] == ORIGIN
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"
