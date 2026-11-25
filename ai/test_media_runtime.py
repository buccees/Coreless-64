import json
from email.message import Message
from urllib.parse import urlsplit

import pytest

from ai.media_runtime import CreatorMediaRuntime

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


class FakeResponse:
    def __init__(self, body, content_type="application/json"):
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.body[:size] if size >= 0 else self.body


def test_worker_generates_and_persists_image_asset(tmp_path, monkeypatch):
    prompt_id = "worker-prompt-1"

    def fake_urlopen(request, timeout=0):
        parsed = urlsplit(request.full_url)
        if parsed.path == "/system_stats":
            return FakeResponse(json.dumps({"system": {"os": "test"}}).encode())
        if parsed.path == "/models/checkpoints":
            return FakeResponse(json.dumps(["photo-checkpoint.safetensors"]).encode())
        if parsed.path == "/prompt":
            payload = json.loads(request.data.decode())
            assert payload["prompt"]["1"]["inputs"]["ckpt_name"] == "photo-checkpoint.safetensors"
            assert payload["prompt"]["2"]["inputs"]["text"] == "A cinematic mountain village"
            return FakeResponse(json.dumps({"prompt_id": prompt_id}).encode())
        if parsed.path == "/history/" + prompt_id:
            history = {prompt_id: {"outputs": {"7": {"images": [{
                "filename": "generated.png", "subfolder": "", "type": "output"
            }]}}, "status": {"status_str": "success"}}}
            return FakeResponse(json.dumps(history).encode())
        if parsed.path == "/view":
            return FakeResponse(PNG, "image/png")
        raise AssertionError("unexpected worker request: " + request.full_url)

    monkeypatch.setattr("ai.media_runtime.urlopen", fake_urlopen)
    runtime = CreatorMediaRuntime(
        endpoint="http://127.0.0.1:8188", library_dir=tmp_path,
        checkpoint="photo-checkpoint.safetensors",
    )
    status = runtime.status()
    assert status["connected"] is True
    assert status["image_ready"] is True
    queued = runtime.submit_image(prompt="A cinematic mountain village")
    completed = runtime.get_job(queued["job_id"])
    assert completed["status"] == "completed"
    assert completed["asset_id"]

    image, content_type, filename = runtime.read_asset(completed["asset_id"])
    assert image == PNG
    assert content_type == "image/png"
    assert filename.endswith(".png")

    restored = CreatorMediaRuntime(endpoint="http://127.0.0.1:8188", library_dir=tmp_path)
    assert restored.list_assets()[0]["asset_id"] == completed["asset_id"]
    assert restored.read_asset(completed["asset_id"])[0] == PNG


def test_worker_refuses_invalid_dimensions_before_network_access(tmp_path):
    runtime = CreatorMediaRuntime(endpoint="http://127.0.0.1:8188", library_dir=tmp_path)
    with pytest.raises(ValueError, match="dimensions"):
        runtime.submit_image(prompt="test", width=513, height=1024)


@pytest.mark.parametrize("endpoint", [
    "http://example.com:8188", "https://127.0.0.1:8188/not-root",
    "http://user:password@127.0.0.1:8188",
])
def test_worker_endpoint_must_be_loopback_without_credentials_or_path(tmp_path, endpoint):
    with pytest.raises(ValueError, match="loopback"):
        CreatorMediaRuntime(endpoint=endpoint, library_dir=tmp_path)


def test_asset_lookup_rejects_path_components(tmp_path):
    runtime = CreatorMediaRuntime(endpoint="http://127.0.0.1:8188", library_dir=tmp_path)
    assert runtime.read_asset("../../secrets") is None
