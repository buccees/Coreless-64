import io
import json
from pathlib import Path

from local_operator_server import SESSION_COOKIE, create_lan_app
from system import CorelessSystem


def _app(password, page, tmp_path):
    system = CorelessSystem(storage_path=tmp_path / "coreless.img")
    system.boot()
    return create_lan_app(password=password, page_path=page, system=system)


def _request(app, path="/", method="GET", body=b"", cookie=None, origin=None):
    from urllib.parse import urlsplit

    parsed_path = urlsplit(path)
    environ = {
        "PATH_INFO": parsed_path.path or "/",
        "QUERY_STRING": parsed_path.query,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_HOST": "127.0.0.1:8443",
        "HTTP_ORIGIN": origin,
    }
    if cookie:
        environ["HTTP_COOKIE"] = cookie
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    result = b"".join(app(environ, start_response))
    return captured, result


def test_lan_host_serves_display_and_requires_session_for_state(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("<!doctype html><title>LAN operator</title>", encoding="utf-8")
    app = _app("a-strong-test-password-123", page, tmp_path)

    response, body = _request(app)
    assert response["status"] == "200 OK"
    assert b"LAN operator" in body

    response, body = _request(app, "/api/operator/state")
    assert response["status"] == "401 Unauthorized"
    assert json.loads(body)["error"] == "unauthorized"


def test_lan_login_creates_secure_cookie_and_state_is_read_only(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("<!doctype html><title>LAN operator</title>", encoding="utf-8")
    app = _app("a-strong-test-password-123", page, tmp_path)

    response, body = _request(
        app,
        "/api/operator/login",
        method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "200 OK"
    cookie = response["headers"]["Set-Cookie"]
    assert cookie.startswith(SESSION_COOKIE + "=")
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=Strict" in cookie
    token = cookie.split(";", 1)[0]

    response, body = _request(app, "/api/operator/state", cookie=token)
    assert response["status"] == "200 OK"
    assert json.loads(body)["protocol_version"] == 1

    response, _ = _request(app, "/api/operator/logout", method="POST", cookie=token, origin="https://127.0.0.1:8443")
    assert response["status"] == "200 OK"
    response, body = _request(app, "/api/operator/state", cookie=token)
    assert response["status"] == "401 Unauthorized"


def test_lan_login_rejects_wrong_password_and_cross_origin(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("display", encoding="utf-8")
    app = _app("a-strong-test-password-123", page, tmp_path)

    response, _ = _request(
        app,
        "/api/operator/login",
        method="POST",
        body=json.dumps({"password": "wrong-password"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "401 Unauthorized"

    response, _ = _request(
        app,
        "/api/operator/login",
        method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://attacker.invalid",
    )
    assert response["status"] == "403 Forbidden"



def test_operator_telemetry_reads_the_injected_machine_instance(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("display", encoding="utf-8")
    system = CorelessSystem(storage_path=tmp_path / "owned-machine.img")
    system.boot()
    calls = []
    original_status = system.status

    def tracked_status():
        calls.append("status")
        return original_status()

    system.status = tracked_status
    app = create_lan_app(
        password="a-strong-test-password-123",
        page_path=page,
        system=system,
    )
    response, _ = _request(
        app,
        "/api/operator/login",
        method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "200 OK"
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]

    response, body = _request(app, "/api/operator/state", cookie=token)
    assert response["status"] == "200 OK"
    assert json.loads(body)["runtime_state"] == "ready"
    assert calls == ["status"]

def test_lan_host_requires_long_password_and_page_exists(tmp_path):
    try:
        create_lan_app(password="too-short", system=None, page_path=tmp_path / "missing.html")
    except ValueError as exc:
        assert "at least 16 characters" in str(exc)
    else:
        raise AssertionError("short operator password should be rejected")

def test_spatial_endpoint_requires_login_and_returns_live_workspace_snapshot(tmp_path):
    from vigil.object_tracking import ObjectObservation, TrackingModality
    from vigil.workspace import SpatialWorkspace
    import json as json_module

    page = tmp_path / "operator-display.html"
    page.write_text("spatial display", encoding="utf-8")
    workspace = SpatialWorkspace()
    manifest = json_module.dumps({
        "schema_version": 1, "model_id": "lab", "revision": "r1",
        "frame_id": "lab/world", "units": "m",
        "features": [
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "bench", "label": "Bench", "position": [8, 4, 0], "level": "L1"},
        ],
    })
    model = workspace.import_blueprint(manifest, activate=True)
    workspace.ingest_object_observations([ObjectObservation(
        "cart-1", "uwb-array", model.model_id, model.revision, model.frame_id,
        __import__("time").monotonic_ns(), (2.0, 1.0, 0.0), 0.2,
        TrackingModality.UWB, "test-calibrated-adapter",
    )])
    app = create_lan_app(
        password="a-strong-test-password-123", page_path=page,
        system=CorelessSystem(storage_path=tmp_path / "owned-machine.img"),
        spatial_workspace=workspace,
    )

    response, body = _request(app, "/api/vigil/spatial")
    assert response["status"] == "401 Unauthorized"
    assert json.loads(body)["error"] == "unauthorized"

    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "200 OK"
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]

    response, body = _request(app, "/api/vigil/spatial", cookie=token)
    assert response["status"] == "200 OK"
    spatial = json.loads(body)
    assert spatial["available"] is True
    assert spatial["model"]["model_id"] == "lab"
    assert spatial["objects"][0]["object_id"] == "cart-1"
    assert spatial["objects"][0]["presence_state"] == "TRACKING"
    assert response["headers"]["Cache-Control"] == "no-store"

    response, body = _request(app, "/api/vigil/spatial", method="POST", cookie=token)
    assert response["status"] == "405 Method Not Allowed"
    assert response["headers"]["Allow"] == "GET"


def test_spatial_endpoint_returns_explicit_unconfigured_status(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("spatial display", encoding="utf-8")
    app = _app("a-strong-test-password-123", page, tmp_path)
    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]
    response, body = _request(app, "/api/vigil/spatial", cookie=token)
    assert response["status"] == "503 Service Unavailable"
    assert json.loads(body)["error"] == "spatial_not_configured"




def test_alert_acknowledgement_requires_auth_and_persists_active_incident(tmp_path):
    import json as json_module
    from vigil.spatial_registry_store import SpatialRegistryStore
    from vigil.workspace import SpatialWorkspace

    page = tmp_path / "operator-display.html"
    page.write_text("spatial display", encoding="utf-8")
    store = SpatialRegistryStore()
    workspace = SpatialWorkspace(registry_store=store)
    workspace.import_blueprint(json_module.dumps({
        "schema_version": 1, "model_id": "lab", "revision": "r1",
        "frame_id": "lab/world", "units": "m",
        "features": [{"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1"}],
    }), activate=True)

    class FailingProvider:
        def read(self):
            raise OSError("camera disconnected")

    workspace.register_sensor_provider("camera-provider", FailingProvider())
    workspace.poll_sensors()
    app = create_lan_app(
        password="a-strong-test-password-123", page_path=page,
        system=CorelessSystem(storage_path=tmp_path / "owned-machine.img"),
        spatial_workspace=workspace,
    )
    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json_module.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]

    response, body = _request(
        app, "/api/vigil/alerts/acknowledge", method="POST",
        body=json_module.dumps({"alert_id": "provider:camera-provider:ERROR"}).encode(),
    )
    assert response["status"] == "401 Unauthorized"

    response, body = _request(app, "/api/vigil/spatial", cookie=token)
    spatial = json_module.loads(body)
    alert = next(item for item in spatial["sensor_health_alerts"] if item["provider_id"] == "camera-provider")
    response, body = _request(
        app, "/api/vigil/alerts/acknowledge", method="POST", cookie=token,
        origin="https://127.0.0.1:8443",
        body=json_module.dumps({"alert_id": alert["alert_id"], "acknowledged": True}).encode(),
    )
    assert response["status"] == "200 OK"
    assert json_module.loads(body)["acknowledged"] is True

    response, body = _request(app, "/api/vigil/spatial", cookie=token)
    spatial = json_module.loads(body)
    alert = next(item for item in spatial["sensor_health_alerts"] if item["provider_id"] == "camera-provider")
    assert alert["acknowledged"] is True
    assert alert["acknowledged_by"] == "authenticated_operator"

    response, body = _request(
        app, "/api/vigil/alerts/acknowledge", method="POST", cookie=token,
        origin="https://127.0.0.1:8443",
        body=json_module.dumps({"alert_id": "provider:stale:ERROR"}).encode(),
    )
    assert response["status"] == "409 Conflict"
    store.close()


def test_seafloor_campaign_api_requires_auth_and_merges_then_exports_shared_survey(tmp_path):
    from vigil.seafloor_campaign_store import SeafloorCampaignStore

    page = tmp_path / "operator-display.html"
    page.write_text("survey display", encoding="utf-8")
    survey_store = SeafloorCampaignStore(tmp_path / "campaign.sqlite3")
    app = create_lan_app(
        password="a-strong-test-password-123",
        page_path=page,
        system=CorelessSystem(storage_path=tmp_path / "owned-machine.img"),
        seafloor_campaign_store=survey_store,
    )
    payload = {
        "schema": "vigil.seafloor-survey",
        "version": 1,
        "report_id": "report-alpha-1",
        "world_seed": "PELAGOS-01",
        "coverage": ["10,11", "10,12"],
        "discoveries": [{
            "id": "PELAGOS-01:entity:10,11", "kind": "SEAMOUNT",
            "x": 0.25, "y": 0.5, "scale": "LOCAL", "seed": "PELAGOS-01",
            "status": "CONFIRMED", "discoveredAt": "2026-10-27T12:00:00Z",
            "depthMeters": 1800,
        }],
    }
    response, body = _request(
        app, "/api/vigil/seafloor-survey", method="POST",
        body=json.dumps(payload).encode(), origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "401 Unauthorized"

    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]
    response, body = _request(
        app, "/api/vigil/seafloor-survey", method="POST", cookie=token,
        origin="https://127.0.0.1:8443", body=json.dumps(payload).encode(),
    )
    assert response["status"] == "200 OK"
    assert json.loads(body)["discoveries_added"] == 1

    response, body = _request(
        app, "/api/vigil/seafloor-survey?world_seed=PELAGOS-01",
        cookie=token, origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "200 OK"
    merged = json.loads(body)
    assert merged["coverage"] == ["10,11", "10,12"]
    assert merged["discoveries"][0]["status"] == "SONAR INDICATION"

    response, body = _request(
        app, "/api/vigil/seafloor-survey", method="POST", cookie=token,
        origin="https://127.0.0.1:8443", body=json.dumps(payload).encode(),
    )
    assert response["status"] == "200 OK"
    assert json.loads(body)["duplicate_report"] is True
    survey_store.close()


def test_seafloor_campaign_api_rejects_cross_origin_and_invalid_payload(tmp_path):
    from vigil.seafloor_campaign_store import SeafloorCampaignStore

    page = tmp_path / "operator-display.html"
    page.write_text("survey display", encoding="utf-8")
    survey_store = SeafloorCampaignStore(tmp_path / "campaign.sqlite3")
    app = create_lan_app(
        password="a-strong-test-password-123",
        page_path=page,
        system=CorelessSystem(storage_path=tmp_path / "owned-machine.img"),
        seafloor_campaign_store=survey_store,
    )
    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]
    payload = {
        "schema": "vigil.seafloor-survey", "version": 1, "report_id": "bad-report",
        "world_seed": "PELAGOS-01", "coverage": [],
        "discoveries": [{"id": "bad", "kind": "WRECK", "x": 2, "y": 0.5,
                         "scale": "LOCAL", "seed": "PELAGOS-01"}],
    }
    response, _ = _request(
        app, "/api/vigil/seafloor-survey", method="POST", cookie=token,
        origin="https://attacker.invalid", body=json.dumps(payload).encode(),
    )
    assert response["status"] == "403 Forbidden"
    response, body = _request(
        app, "/api/vigil/seafloor-survey", method="POST", cookie=token,
        origin="https://127.0.0.1:8443", body=json.dumps(payload).encode(),
    )
    assert response["status"] == "400 Bad Request"
    survey_store.close()


def test_historical_artifact_inventory_is_persistent_and_session_protected(tmp_path):
    from vigil.historical_artifact_catalog import build_artifact_catalog
    from vigil.historical_artifact_store import HistoricalArtifactStore

    page = tmp_path / "operator-display.html"
    page.write_text("artifact display", encoding="utf-8")
    db = tmp_path / "artifacts.sqlite3"
    store = HistoricalArtifactStore(build_artifact_catalog(), db)
    app = create_lan_app(
        password="a-strong-test-password-123",
        page_path=page,
        system=CorelessSystem(storage_path=tmp_path / "owned-machine.img"),
        historical_artifact_store=store,
        artifact_unit_action_authorizer=lambda crew_id, unit_id, action: True,
    )

    response, body = _request(app, "/api/vigil/historical-artifacts?world_seed=PELAGOS-01")
    assert response["status"] == "401 Unauthorized"
    assert json.loads(body)["error"] == "unauthorized"

    response, body = _request(
        app, "/api/operator/login", method="POST",
        body=json.dumps({"password": "a-strong-test-password-123"}).encode(),
        origin="https://127.0.0.1:8443",
    )
    assert response["status"] == "200 OK"
    token = response["headers"]["Set-Cookie"].split(";", 1)[0]

    response, body = _request(app, "/api/vigil/historical-artifacts?world_seed=PELAGOS-01", cookie=token)
    assert response["status"] == "200 OK"
    payload = json.loads(body)
    assert payload["count"] == 6
    assert all(item["unique"] and not item["respawnable"] for item in payload["artifacts"])
    assert payload["artifacts"][0]["location"] is None
    assert payload["artifacts"][0]["sourceSiteId"] is None
    assert payload["artifacts"][0]["discovered"] is False

    response, body = _request(
        app, "/api/vigil/historical-artifacts", method="POST", cookie=token,
        origin="https://127.0.0.1:8443",
        body=json.dumps({"world_seed": "PELAGOS-01", "action": "collect",
                         "artifact_id": "PEL-ARCHIVE-EXPEDITION-HANDBOOK",
                         "unit_id": "UUV-01"}).encode(),
    )
    assert response["status"] == "503 Service Unavailable"
    assert json.loads(body)["error"] == "authoritative_unit_state_unavailable"

    store.close()
