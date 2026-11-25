import json
from email.message import Message
from urllib.parse import urlsplit

import pytest

from ai.media_runtime import CreatorMediaRuntime

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 16


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


def test_worker_generates_and_persists_video_asset(tmp_path, monkeypatch):
    prompt_id = "worker-video-prompt"
    workflow_path = tmp_path / "video-workflow.json"
    workflow_path.write_text(json.dumps({
        "1": {"class_type": "SaveVideo", "inputs": {
            "prompt": "__PROMPT__", "frames": "__FRAMES__", "fps": "__FPS__",
            "width": "__WIDTH__", "height": "__HEIGHT__", "seed": "__SEED__",
        }}
    }), encoding="utf-8")

    def fake_urlopen(request, timeout=0):
        parsed = urlsplit(request.full_url)
        if parsed.path == "/system_stats":
            return FakeResponse(json.dumps({"system": {"os": "test"}}).encode())
        if parsed.path == "/models/checkpoints":
            return FakeResponse(json.dumps(["photo-checkpoint.safetensors"]).encode())
        if parsed.path == "/prompt":
            payload = json.loads(request.data.decode())
            inputs = payload["prompt"]["1"]["inputs"]
            assert inputs["prompt"] == "A slow cinematic ocean flyover"
            assert inputs["frames"] == 81
            assert inputs["fps"] == 16
            assert inputs["width"] == 640 and inputs["height"] == 360
            return FakeResponse(json.dumps({"prompt_id": prompt_id}).encode())
        if parsed.path == "/history/" + prompt_id:
            history = {prompt_id: {"outputs": {"9": {"videos": [{
                "filename": "generated.mp4", "subfolder": "", "type": "output"
            }]}}, "status": {"status_str": "success", "completed": True}}}
            return FakeResponse(json.dumps(history).encode())
        if parsed.path == "/view":
            return FakeResponse(MP4, "video/mp4")
        raise AssertionError("unexpected worker request: " + request.full_url)

    monkeypatch.setattr("ai.media_runtime.urlopen", fake_urlopen)
    runtime = CreatorMediaRuntime(
        endpoint="http://127.0.0.1:8188", library_dir=tmp_path / "assets",
        checkpoint="photo-checkpoint.safetensors", video_workflow_path=workflow_path,
    )
    status = runtime.status()
    assert status["connected"] is True
    assert status["video_ready"] is True

    queued = runtime.submit_video(
        prompt="A slow cinematic ocean flyover", width=640, height=360, frames=81, fps=16
    )
    completed = runtime.get_job(queued["job_id"])
    assert completed["status"] == "completed"
    assert completed["media_type"] == "video"
    assert completed["duration_seconds"] == 5.0
    assert completed["asset_id"]

    video, content_type, filename = runtime.read_asset(completed["asset_id"])
    assert video == MP4
    assert content_type == "video/mp4"
    assert filename.endswith(".mp4")
    asset = runtime.list_assets()[0]
    assert asset["media_type"] == "video" and asset["fps"] == 16

    restored = CreatorMediaRuntime(
        endpoint="http://127.0.0.1:8188", library_dir=tmp_path / "assets",
        video_workflow_path=workflow_path,
    )
    assert restored.list_assets()[0]["asset_id"] == completed["asset_id"]
    assert restored.read_asset(completed["asset_id"])[0] == MP4


def test_video_workflow_requires_supported_output_node(tmp_path, monkeypatch):
    workflow_path = tmp_path / "video-workflow.json"
    workflow_path.write_text(json.dumps({"1": {"class_type": "KSampler", "inputs": {}}}), encoding="utf-8")

    def fake_urlopen(request, timeout=0):
        parsed = urlsplit(request.full_url)
        if parsed.path == "/system_stats":
            return FakeResponse(json.dumps({"system": {"os": "test"}}).encode())
        if parsed.path == "/models/checkpoints":
            return FakeResponse(json.dumps(["photo-checkpoint.safetensors"]).encode())
        raise AssertionError("video workflow should be rejected before submission")

    monkeypatch.setattr("ai.media_runtime.urlopen", fake_urlopen)
    runtime = CreatorMediaRuntime(
        endpoint="http://127.0.0.1:8188", library_dir=tmp_path,
        video_workflow_path=workflow_path,
    )
    assert runtime.status()["connected"] is True
    assert runtime.status()["video_ready"] is False
    with pytest.raises(RuntimeError, match="video workflow"):
        runtime.submit_video(prompt="test")

