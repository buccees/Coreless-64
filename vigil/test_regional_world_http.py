import io
import json

from vigil.regional_world import RegionalShip, RegionalWorld
from vigil.regional_world_http import create_regional_snapshot_app

ORIGIN = "https://vigil.example.test"


def request(app, path="/api/regional/snapshot", *, method="GET", token=None, origin=ORIGIN):
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
        "HTTP_ORIGIN": origin,
    }
    if token:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    result = {}

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = dict(headers)

    result["body"] = b"".join(app(environ, start_response))
    result["json"] = json.loads(result["body"] or b"{}")
    return result


def make_world():
    return RegionalWorld([
        RegionalShip(
            ship_id="friendly", name="Friendly", x=50, y=25, speed=4,
            max_hull=5, ship_class="destroyer", length_m=100, beam_m=20,
            heading_deg=90, blueprint_source="test source",
        ),
        RegionalShip(
            ship_id="hidden", name="Hidden contact", x=70, y=30, speed=2,
            max_hull=4, ship_class="submarine",
        ),
    ])


def test_snapshot_endpoint_returns_only_authorized_ships_and_no_store():
    app = create_regional_snapshot_app(
        world=make_world(),
        allowed_origins=[ORIGIN],
        visible_ships_for_token=lambda token: {"friendly"} if token == "valid" else None,
        world_bounds=(0, 0, 100, 100),
    )
    result = request(app, token="valid")
    assert result["status"] == "200 OK"
    assert result["headers"]["Cache-Control"] == "no-store"
    assert result["json"]["schema_version"] == 1
    assert result["json"]["ships"][0]["ship_id"] == "friendly"
    assert result["json"]["ships"][0]["normalized_position"] == [0.5, 0.25]
    assert "Hidden contact" not in result["body"].decode()


def test_snapshot_endpoint_rejects_missing_or_invalid_token_and_wrong_origin():
    app = create_regional_snapshot_app(
        world=make_world(),
        allowed_origins=[ORIGIN],
        visible_ships_for_token=lambda token: {"friendly"} if token == "valid" else None,
        world_bounds=(0, 0, 100, 100),
    )
    assert request(app)["status"] == "401 Unauthorized"
    assert request(app, token="bad")["status"] == "401 Unauthorized"
    assert request(app, token="valid", origin="https://evil.example")["status"] == "403 Forbidden"


def test_snapshot_endpoint_rejects_unknown_paths_and_methods():
    app = create_regional_snapshot_app(
        world=make_world(), allowed_origins=[ORIGIN],
        visible_ships_for_token=lambda token: {"friendly"},
    )
    assert request(app, path="/unknown", token="valid")["status"] == "404 Not Found"
    assert request(app, method="POST", token="valid")["status"] == "405 Method Not Allowed"
