import io
import json

import pytest

from vigil.multiplayer import BattleshipRooms
from vigil.multiplayer_http import create_multiplayer_app


ORIGIN = "https://vigil.example.test"
FLEET = [
    [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]],
    [[1, 0], [1, 1], [1, 2], [1, 3]],
    [[2, 0], [2, 1], [2, 2]],
    [[3, 0], [3, 1], [3, 2]],
    [[4, 0], [4, 1]],
]


def request(app, path, *, method="GET", payload=None, token=None, origin=ORIGIN):
    body = json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_ORIGIN": origin,
    }
    if token:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    result = {}

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = dict(headers)

    result["body"] = b"".join(app(environ, start_response))
    result["json"] = json.loads(result["body"])
    return result


def test_api_creates_and_joins_room_then_enforces_turns():
    app = create_multiplayer_app(allowed_origins=[ORIGIN], rooms=BattleshipRooms())
    first = request(app, "/api/multiplayer/create", method="POST", payload={"fleet": FLEET})
    assert first["status"] == "201 Created"
    second = request(
        app, "/api/multiplayer/join", method="POST",
        payload={"room_code": first["json"]["room_code"], "fleet": FLEET},
    )
    assert second["status"] == "200 OK"
    assert first["json"]["player_token"] != second["json"]["player_token"]

    denied = request(app, "/api/multiplayer/fire", method="POST",
                     payload={"row": 0, "column": 0}, token=second["json"]["player_token"])
    assert denied["status"] == "400 Bad Request"
    shot = request(app, "/api/multiplayer/fire", method="POST",
                   payload={"row": 0, "column": 0}, token=first["json"]["player_token"])
    assert shot["status"] == "200 OK"
    assert shot["json"]["outgoing_shots"][0]["hit"] is True

    view = request(app, "/api/multiplayer/state", token=second["json"]["player_token"])
    assert view["status"] == "200 OK"
    assert view["json"]["incoming_shots"] == [{"row": 0, "column": 0}]
    assert "hit" not in view["json"]["incoming_shots"][0]


def test_api_rejects_wrong_origin_missing_token_and_bad_methods():
    app = create_multiplayer_app(allowed_origins=[ORIGIN])
    wrong_origin = request(app, "/api/multiplayer/create", method="POST",
                           payload={"fleet": FLEET}, origin="https://attacker.test")
    assert wrong_origin["status"] == "403 Forbidden"

    no_token = request(app, "/api/multiplayer/state")
    assert no_token["status"] == "401 Unauthorized"

    wrong_method = request(app, "/api/multiplayer/create", method="GET")
    assert wrong_method["status"] == "405 Method Not Allowed"


def test_api_requires_exact_https_origins():
    with pytest.raises(ValueError, match="exact HTTPS origins"):
        create_multiplayer_app(allowed_origins=["*"])
    with pytest.raises(ValueError, match="exact HTTPS origins"):
        create_multiplayer_app(allowed_origins=["http://vigil.example.test"])
