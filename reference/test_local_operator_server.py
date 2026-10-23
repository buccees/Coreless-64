import io
import json
from pathlib import Path

from local_operator_server import SESSION_COOKIE, create_lan_app


def _request(app, path="/", method="GET", body=b"", cookie=None, origin=None):
    environ = {
        "PATH_INFO": path,
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
    app = create_lan_app(password="a-strong-test-password-123", page_path=page)

    response, body = _request(app)
    assert response["status"] == "200 OK"
    assert b"LAN operator" in body

    response, body = _request(app, "/api/operator/state")
    assert response["status"] == "401 Unauthorized"
    assert json.loads(body)["error"] == "unauthorized"


def test_lan_login_creates_secure_cookie_and_state_is_read_only(tmp_path):
    page = tmp_path / "operator-display.html"
    page.write_text("<!doctype html><title>LAN operator</title>", encoding="utf-8")
    app = create_lan_app(password="a-strong-test-password-123", page_path=page)

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
    app = create_lan_app(password="a-strong-test-password-123", page_path=page)

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


def test_lan_host_requires_long_password_and_page_exists(tmp_path):
    try:
        create_lan_app(password="too-short", page_path=tmp_path / "missing.html")
    except ValueError as exc:
        assert "at least 16 characters" in str(exc)
    else:
        raise AssertionError("short operator password should be rejected")
