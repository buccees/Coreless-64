import json
import sys
sys.path.insert(0, ".")
import pytest

from operator_display import OperatorViewState
from operator_telemetry import (
    CorelessOperatorSnapshotProvider,
    OperatorTelemetryApp,
    coreless_view_state,
    create_coreless_operator_app,
)


def _call(app, path="/api/operator/state", method="GET", origin=None,
          requested_method=None, requested_headers=None):
    captured = {}
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "HTTP_COOKIE": "session=opaque",
    }
    if origin is not None:
        environ["HTTP_ORIGIN"] = origin
    if requested_method is not None:
        environ["HTTP_ACCESS_CONTROL_REQUEST_METHOD"] = requested_method
    if requested_headers is not None:
        environ["HTTP_ACCESS_CONTROL_REQUEST_HEADERS"] = requested_headers
    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    body = b"".join(app(environ, start_response))
    return captured, body


def _state():
    return OperatorViewState(
        sequence=1,
        generated_at_ns=100,
        source_timestamp_ns=100,
        connection_state="connected",
        runtime_state="ready",
    )


def test_endpoint_returns_read_only_versioned_json_without_cache():
    app = OperatorTelemetryApp(lambda: _state(), authorize=lambda env: True)
    response, body = _call(app)
    assert response["status"] == "200 OK"
    assert response["headers"]["Cache-Control"] == "no-store"
    assert json.loads(body)["protocol_version"] == 1
    assert json.loads(body)["sensors"] == []


def test_endpoint_fails_closed_before_reading_telemetry():
    calls = []
    app = OperatorTelemetryApp(
        lambda: calls.append("read") or _state(),
        authorize=lambda env: False,
    )
    response, body = _call(app)
    assert response["status"] == "401 Unauthorized"
    assert json.loads(body)["error"] == "unauthorized"
    assert calls == []


def test_authorizer_exception_fails_closed():
    def broken_authorizer(env):
        raise RuntimeError("session store unavailable")
    app = OperatorTelemetryApp(lambda: _state(), authorize=broken_authorizer)
    response, _ = _call(app)
    assert response["status"] == "401 Unauthorized"


def test_endpoint_rejects_non_get_methods():
    app = OperatorTelemetryApp(lambda: _state(), authorize=lambda env: True)
    response, _ = _call(app, method="POST")
    assert response["status"] == "405 Method Not Allowed"


def test_endpoint_hides_unmatched_routes():
    app = OperatorTelemetryApp(lambda: _state(), authorize=lambda env: True)
    response, _ = _call(app, path="/api/operator/commands")
    assert response["status"] == "404 Not Found"


def test_endpoint_returns_service_unavailable_for_bad_provider():
    app = OperatorTelemetryApp(lambda: {"not": "a state"}, authorize=lambda env: True)
    response, body = _call(app)
    assert response["status"] == "503 Service Unavailable"
    assert json.loads(body)["error"] == "telemetry_unavailable"


def test_runtime_adapter_reports_lifecycle_without_fabricating_sensors():
    class Machine:
        booted = False
    class System:
        machine = Machine()
        def status(self):
            return {"runtime": "reference"}
    state = coreless_view_state(System(), sequence=4)
    assert state.sequence == 4
    assert state.runtime_state == "starting"
    assert state.sensors == ()
    assert state.alerts == ()


def test_runtime_adapter_requires_existing_system_status():
    with pytest.raises(TypeError, match="CorelessSystem.status"):
        coreless_view_state(object())


def test_coreless_provider_sequences_snapshots_without_fabricating_sensor_data():
    class Machine:
        booted = True
    class System:
        machine = Machine()
        def status(self):
            return {"runtime": "reference"}
    provider = CorelessOperatorSnapshotProvider(System())
    first = provider()
    second = provider()
    assert first.sequence == 0
    assert second.sequence == 1
    assert first.runtime_state == "ready"
    assert first.sensors == ()
    assert first.alerts == ()


def test_factory_binds_existing_coreless_system_to_authorized_endpoint():
    class Machine:
        booted = True
    class System:
        machine = Machine()
        def status(self):
            return {"runtime": "reference"}
    app = create_coreless_operator_app(System(), authorize=lambda env: True)
    response, body = _call(app)
    assert response["status"] == "200 OK"
    decoded = json.loads(body)
    assert decoded["runtime_state"] == "ready"
    assert decoded["sequence"] == 0


def test_provider_requires_coreless_status_api():
    with pytest.raises(TypeError, match="CorelessSystem.status"):
        CorelessOperatorSnapshotProvider(object())


def test_real_coreless_system_can_back_read_only_operator_endpoint(tmp_path):
    from system import CorelessSystem

    system = CorelessSystem(storage_path=tmp_path / "operator-display.json")
    app = create_coreless_operator_app(system, authorize=lambda env: True)
    response, body = _call(app)
    assert response["status"] == "200 OK"
    decoded = json.loads(body)
    assert decoded["protocol_version"] == 1
    assert decoded["runtime_state"] == "starting"
    assert decoded["sensors"] == []
    assert decoded["alerts"] == []
    system.boot()
    response, body = _call(app)
    assert response["status"] == "200 OK"
    decoded = json.loads(body)
    assert decoded["runtime_state"] == "ready"
    assert decoded["sequence"] == 1


def test_cors_allows_only_explicit_https_origin_with_credentials():
    app = OperatorTelemetryApp(
        lambda: _state(),
        authorize=lambda env: True,
        allowed_origins=("https://buccees.github.io",),
    )
    response, body = _call(app, origin="https://buccees.github.io")
    assert response["status"] == "200 OK"
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://buccees.github.io"
    assert response["headers"]["Access-Control-Allow-Credentials"] == "true"
    assert response["headers"]["Vary"] == "Cookie, Authorization, Origin"


def test_cors_rejects_unlisted_origin_before_authorization_or_snapshot():
    calls = []
    app = OperatorTelemetryApp(
        lambda: calls.append("snapshot") or _state(),
        authorize=lambda env: calls.append("authorize") or True,
        allowed_origins=("https://buccees.github.io",),
    )
    response, body = _call(app, origin="https://attacker.example")
    assert response["status"] == "403 Forbidden"
    assert json.loads(body)["error"] == "origin_not_allowed"
    assert calls == []


def test_cors_preflight_is_allowlisted_and_read_only():
    app = OperatorTelemetryApp(
        lambda: _state(),
        authorize=lambda env: True,
        allowed_origins=("https://buccees.github.io",),
    )
    response, body = _call(
        app, method="OPTIONS", origin="https://buccees.github.io",
        requested_method="GET", requested_headers="Accept",
    )
    assert response["status"] == "204 No Content"
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET, OPTIONS"
    assert body == b""


@pytest.mark.parametrize("origin", [
    "http://buccees.github.io",
    "https://buccees.github.io/",
    "https://buccees.github.io/path",
    "https://user@buccees.github.io",
    "https://buccees.github.io?x=1",
    "https://buccees.github.io#fragment",
    "https://",
    "https://buccees.github.io:invalid",
])
def test_cors_rejects_malformed_or_non_https_allowlist_configuration(origin):
    with pytest.raises(ValueError, match="valid HTTPS origins"):
        OperatorTelemetryApp(
            lambda: _state(), authorize=lambda env: True,
            allowed_origins=(origin,),
        )


def test_cors_rejects_unlisted_origin_for_options():
    app = OperatorTelemetryApp(
        lambda: _state(), authorize=lambda env: True,
        allowed_origins=("https://buccees.github.io",),
    )
    response, _ = _call(
        app, method="OPTIONS", origin="https://attacker.example",
        requested_method="GET",
    )
    assert response["status"] == "403 Forbidden"


def test_cors_preflight_rejects_unapproved_request_headers():
    app = OperatorTelemetryApp(
        lambda: _state(), authorize=lambda env: True,
        allowed_origins=("https://buccees.github.io",),
    )
    response, body = _call(
        app, method="OPTIONS", origin="https://buccees.github.io",
        requested_method="GET", requested_headers="Authorization, X-Custom",
    )
    assert response["status"] == "400 Bad Request"
    assert json.loads(body)["error"] == "headers_not_allowed"
