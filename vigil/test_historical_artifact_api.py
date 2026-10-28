"""HTTP-level tests for the authenticated historical artifact API."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from vigil.historical_artifact_api import make_historical_artifact_handler
from vigil.historical_artifact_store import HistoricalArtifactStore


def unit(unit_id, x, y, side="blue"):
    return {"id": unit_id, "unitType": "submersible", "x": x, "y": y,
            "side": side, "afloat": True,
            "lockedArtifactContainer": {"locked": True, "artifactIds": []}}


class HistoricalArtifactApiTests(unittest.TestCase):
    def setUp(self):
        self.store = HistoricalArtifactStore([
            {"id": "ART-ONE", "siteId": "SITE-ONE", "x": .2, "y": .3}
        ])
        self.units = {
            "UUV-1": unit("UUV-1", .2, .3, "blue"),
            "UUV-2": unit("UUV-2", .21, .3, "red"),
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_historical_artifact_handler(
            self.store,
            authenticate=lambda request: "crew-blue" if request.headers.get("X-Test-Auth") == "valid" else None,
            resolve_unit=lambda unit_id: self.units.get(unit_id),
            authorize_unit_action=lambda crew, unit_id, action: crew == "crew-blue" and unit_id == "UUV-1",
            authorize_custody_action=lambda crew, source, target, action:
                crew == "crew-blue" and ((action == "capture" and target == "UUV-1") or (action == "transfer" and source == "UUV-1" and target == "UUV-1")),
            authorize_discovery=lambda crew, seed, artifact: crew == "crew-blue" and artifact == "ART-ONE",
            validate_sinking_event=lambda seed, uid, event_id:
                {"x": .25, "y": .35} if (uid, event_id) == ("UUV-1", "sink-1") else None,
        ))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.store.close()

    def request(self, path, *, method="GET", body=None, auth=True):
        headers = {}
        if auth:
            headers["X-Test-Auth"] = "valid"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=3)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())
        return response.status, json.loads(response.read().decode())

    def test_inventory_requires_authentication(self):
        status, payload = self.request("/artifacts?world_seed=PELAGOS-01", auth=False)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "authentication_required")
        status, payload = self.request("/artifacts?world_seed=PELAGOS-01")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 1)

    def test_client_cannot_supply_fake_unit_coordinates(self):
        status, payload = self.request("/artifacts/action", method="POST", body={
            "world_seed": "PELAGOS-01", "action": "discover", "artifact_id": "ART-ONE"
        })
        self.assertEqual(status, 200)
        status, payload = self.request("/artifacts/action", method="POST", body={
            "world_seed": "PELAGOS-01", "action": "collect", "artifact_id": "ART-ONE",
            "unit_id": "UUV-1", "unit": {"id": "UUV-1", "x": .99, "y": .99}
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload["artifact"]["carrierId"], "UUV-1")
        self.assertEqual(payload["artifact"]["location"], {"x": .2, "y": .3})

    def test_unauthorized_unit_and_invalid_sink_event_are_denied(self):
        status, payload = self.request("/artifacts/action", method="POST", body={
            "world_seed": "PELAGOS-01", "action": "collect", "artifact_id": "ART-ONE",
            "unit_id": "UUV-2"
        })
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "unit_not_authorized")
        status, payload = self.request("/artifacts/action", method="POST", body={
            "world_seed": "PELAGOS-01", "action": "drop_on_sinking", "artifact_id": "ART-ONE",
            "unit_id": "UUV-1", "sinking_event_id": "fake"
        })
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "sinking_event_not_authorized")

    def test_body_limit_and_unknown_routes(self):
        status, payload = self.request("/missing")
        self.assertEqual(status, 404)
        req = Request(self.base + "/artifacts/action", data=b"x" * 16385,
                      headers={"X-Test-Auth": "valid", "Content-Length": "16385"}, method="POST")
        try:
            urlopen(req, timeout=3)
            self.fail("oversized body should be rejected")
        except HTTPError as exc:
            self.assertEqual(exc.code, 409)


if __name__ == "__main__":
    unittest.main()
