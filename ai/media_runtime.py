"""Creator Studio local media inference adapter.

The Coreless local server remains the user-facing API and security boundary.
This adapter delegates image inference to a ComfyUI worker bound to loopback
on the Coreless host. Model weights and generated assets stay outside Git.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid


class CreatorMediaRuntime:
    """Generate real images through a locally hosted ComfyUI API worker."""

    def __init__(
        self, *, endpoint: str | None = None, library_dir: str | Path | None = None,
        checkpoint: str | None = None, workflow_path: str | Path | None = None,
        token: str | None = None, timeout: float = 12.0,
    ) -> None:
        self.endpoint = (endpoint or os.getenv(
            "CORELESS_MEDIA_ENGINE_URL", "http://127.0.0.1:8188"
        )).rstrip("/")
        parsed = urlsplit(self.endpoint)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment
        ):
            raise ValueError("media engine must be an HTTP(S) loopback URL without credentials or a path")
        self.library_dir = Path(library_dir or os.getenv(
            "CORELESS_CREATOR_LIBRARY_DIR",
            Path(__file__).resolve().parents[1] / "data" / "creator-assets",
        )).expanduser()
        self.checkpoint = checkpoint or os.getenv("CORELESS_MEDIA_IMAGE_CHECKPOINT", "")
        configured_workflow = workflow_path or os.getenv("CORELESS_MEDIA_IMAGE_WORKFLOW", "")
        self.workflow_path = Path(configured_workflow).expanduser() if configured_workflow else None
        self.token = token or os.getenv("CORELESS_MEDIA_ENGINE_TOKEN")
        self.timeout = max(1.0, float(timeout))
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}
        self._assets: dict[str, dict] = {}
        self._index_path = self.library_dir / "index.json"
        self._load_index()

    @classmethod
    def from_environment(cls) -> "CreatorMediaRuntime":
        return cls()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    def _json_request(self, method: str, path: str, payload: dict | None = None):
        headers = self._headers()
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(self.endpoint + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise RuntimeError("local image worker returned an oversized response")
            return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError("local image worker returned HTTP " + str(exc.code)) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("local image worker is unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("local image worker returned invalid JSON") from exc

    def _binary_request(self, path: str) -> tuple[bytes, str]:
        headers = {"Accept": "image/png,image/jpeg,image/webp"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            with urlopen(Request(self.endpoint + path, headers=headers), timeout=max(self.timeout, 60.0)) as response:
                content_type = response.headers.get_content_type()
                data = response.read(100 * 1024 * 1024 + 1)
        except HTTPError as exc:
            raise RuntimeError("local worker could not return the generated image (HTTP " + str(exc.code) + ")") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("generated image could not be retrieved") from exc
        if len(data) > 100 * 1024 * 1024:
            raise RuntimeError("generated image exceeds the 100 MB limit")
        valid = (
            (content_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
            or (content_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
            or (content_type == "image/webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
        )
        if not valid:
            raise RuntimeError("local worker did not return a valid PNG, JPEG, or WebP image")
        return data, content_type

    def _load_index(self) -> None:
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("Creator Studio asset index is unreadable") from exc
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("assets"), list):
            raise RuntimeError("Creator Studio asset index has an unsupported format")
        for item in data["assets"]:
            if not isinstance(item, dict):
                continue
            asset_id, filename = item.get("asset_id"), item.get("filename")
            if (
                isinstance(asset_id, str) and len(asset_id) == 32
                and all(c in "0123456789abcdef" for c in asset_id)
                and isinstance(filename, str) and Path(filename).name == filename
            ):
                self._assets[asset_id] = item

    def _save_index(self) -> None:
        self.library_dir.mkdir(parents=True, exist_ok=True)
        temporary = self._index_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(
            {"version": 1, "assets": list(self._assets.values())},
            indent=2, sort_keys=True,
        ), encoding="utf-8")
        temporary.replace(self._index_path)

    def _custom_workflow(self) -> dict | None:
        if self.workflow_path is None or not self.workflow_path.is_file():
            return None
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        if isinstance(workflow, dict) and isinstance(workflow.get("prompt"), dict):
            workflow = workflow["prompt"]
        if not isinstance(workflow, dict) or not workflow:
            raise RuntimeError("configured image workflow must be a ComfyUI API prompt object")
        return workflow

    @staticmethod
    def _replace_tokens(value, replacements):
        if isinstance(value, dict):
            return {key: CreatorMediaRuntime._replace_tokens(item, replacements) for key, item in value.items()}
        if isinstance(value, list):
            return [CreatorMediaRuntime._replace_tokens(item, replacements) for item in value]
        if isinstance(value, str) and value in replacements:
            return replacements[value]
        return value

    def status(self) -> dict:
        try:
            stats = self._json_request("GET", "/system_stats")
            models = self._json_request("GET", "/models/checkpoints")
            if not isinstance(stats, dict) or not isinstance(models, list):
                raise RuntimeError("local image worker returned an invalid status")
            names = sorted({
                name if isinstance(name, str) else name.get("name")
                for name in models
                if (isinstance(name, str) and name.strip())
                or (isinstance(name, dict) and isinstance(name.get("name"), str) and name.get("name").strip())
            })
            custom = self._custom_workflow()
            selected = self.checkpoint or (names[0] if names else "")
            ready = bool(selected and selected in names) or custom is not None
            choices = [{"value": name, "label": name} for name in names]
            if custom is not None:
                choices.insert(0, {"value": "__custom_workflow__", "label": "Configured custom workflow"})
            return {
                "connected": True, "provider": "Coreless local media worker",
                "worker": "ComfyUI", "image_ready": ready, "image_models": names,
                "image_choices": choices,
                "selected_image_model": selected if selected in names else (
                    "__custom_workflow__" if custom is not None else ""
                ),
                "custom_workflow": custom is not None,
                "video_ready": False,
                "detail": (
                    "Image worker and model workflow are ready."
                    if ready else "Worker is online, but no configured image checkpoint or custom workflow is available."
                ),
                "asset_count": len(self._assets),
            }
        except (RuntimeError, ValueError, OSError):
            return {
                "connected": False, "provider": "Coreless local media worker",
                "worker": "ComfyUI", "image_ready": False, "image_models": [],
                "image_choices": [], "selected_image_model": "", "custom_workflow": False,
                "video_ready": False,
                "detail": "Start the configured local image worker to connect Creator Studio.",
                "asset_count": len(self._assets),
            }

    @staticmethod
    def _default_workflow(prompt: str, negative_prompt: str, model: str, width: int,
                          height: int, steps: int, cfg: float, seed: int) -> dict:
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m",
                "scheduler": "karras", "denoise": 1.0, "model": ["1", 0],
                "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
            }},
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "coreless-creator", "images": ["6", 0]}},
        }

    def submit_image(
        self, *, prompt: str, model: str = "",
        negative_prompt: str = "blurry, low detail, distorted anatomy, artifacts, text, watermark",
        width: int = 1024, height: int = 1024, steps: int = 30, cfg: float = 6.5,
    ) -> dict:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 5000:
            raise ValueError("prompt must contain 1 to 5000 characters")
        if not isinstance(negative_prompt, str) or len(negative_prompt) > 2000:
            raise ValueError("negative prompt must be 2000 characters or fewer")
        if any(not isinstance(v, int) or v < 512 or v > 1536 or v % 64 for v in (width, height)):
            raise ValueError("image dimensions must be multiples of 64 from 512 to 1536")
        if not isinstance(steps, int) or not 1 <= steps <= 80:
            raise ValueError("sampling steps must be from 1 to 80")
        if not isinstance(cfg, (int, float)) or not 1 <= float(cfg) <= 20:
            raise ValueError("CFG must be from 1 to 20")
        status = self.status()
        if not status["connected"] or not status["image_ready"]:
            raise RuntimeError(status["detail"])
        selected = model or status["selected_image_model"]
        custom = selected == "__custom_workflow__"
        seed = secrets.randbelow(2**63 - 1)
        if custom:
            base = self._custom_workflow()
            if base is None:
                raise RuntimeError("configured custom image workflow is unavailable")
            workflow = self._replace_tokens(base, {
                "__PROMPT__": prompt.strip(), "__NEGATIVE_PROMPT__": negative_prompt,
                "__MODEL__": self.checkpoint, "__WIDTH__": width, "__HEIGHT__": height,
                "__STEPS__": steps, "__CFG__": float(cfg), "__SEED__": seed,
            })
            model_label = "Configured custom workflow"
        else:
            if selected not in status["image_models"]:
                raise ValueError("selected image model is not installed in the local worker")
            workflow = self._default_workflow(
                prompt.strip(), negative_prompt, selected, width, height, steps, float(cfg), seed
            )
            model_label = selected
        response = self._json_request("POST", "/prompt", {
            "prompt": workflow, "client_id": "coreless-creator-studio",
        })
        prompt_id = response.get("prompt_id") if isinstance(response, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            details = response.get("node_errors") if isinstance(response, dict) else None
            raise RuntimeError("local image worker rejected the workflow: " + (str(details)[:400] if details else "no prompt ID returned"))
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id, "prompt_id": prompt_id, "status": "queued",
            "created": datetime.now(timezone.utc).isoformat(), "prompt": prompt.strip(),
            "model": model_label, "width": width, "height": height, "steps": steps,
            "cfg": float(cfg), "seed": seed, "asset_id": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        return {"job_id": job_id, "status": "queued", "seed": seed}

    def get_job(self, job_id: str) -> dict | None:
        if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            return None
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job["status"] in ("completed", "failed"):
                return dict(job)
        try:
            history = self._json_request("GET", "/history/" + quote(job["prompt_id"], safe=""))
            record = history.get(job["prompt_id"]) if isinstance(history, dict) else None
            if not isinstance(record, dict):
                return dict(job)
            outputs = record.get("outputs")
            image_info = None
            if isinstance(outputs, dict):
                for node in outputs.values():
                    images = node.get("images") if isinstance(node, dict) else None
                    if isinstance(images, list) and images and isinstance(images[0], dict):
                        image_info = images[0]
                        break
            if image_info:
                query = urlencode({
                    "filename": str(image_info.get("filename", "")),
                    "subfolder": str(image_info.get("subfolder", "")),
                    "type": str(image_info.get("type", "output")),
                })
                raw, content_type = self._binary_request("/view?" + query)
                extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[content_type]
                asset_id = uuid.uuid4().hex
                filename = asset_id + extension
                self.library_dir.mkdir(parents=True, exist_ok=True)
                (self.library_dir / filename).write_bytes(raw)
                now = datetime.now(timezone.utc).isoformat()
                asset = {
                    "asset_id": asset_id, "filename": filename, "content_type": content_type,
                    "title": "Generated image", "model": job["model"], "prompt": job["prompt"],
                    "width": job["width"], "height": job["height"], "seed": job["seed"], "created": now,
                }
                with self._lock:
                    self._assets[asset_id] = asset
                    self._save_index()
                    job["status"] = "completed"
                    job["asset_id"] = asset_id
                    job["completed"] = now
                    return dict(job)
            status = record.get("status", {})
            if isinstance(status, dict) and status.get("status_str") == "error":
                with self._lock:
                    job["status"] = "failed"
                    job["error"] = "The image worker reported a generation error."
                    return dict(job)
            with self._lock:
                job["status"] = "running"
                return dict(job)
        except (RuntimeError, OSError, ValueError):
            with self._lock:
                job["status"] = "failed"
                job["error"] = "Image generation failed while retrieving the worker result."
                return dict(job)

    def list_assets(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in sorted(
                self._assets.values(), key=lambda item: item.get("created", ""), reverse=True
            )]

    def read_asset(self, asset_id: str) -> tuple[bytes, str, str] | None:
        if not isinstance(asset_id, str) or len(asset_id) != 32 or any(c not in "0123456789abcdef" for c in asset_id):
            return None
        with self._lock:
            item = self._assets.get(asset_id)
            if item is None:
                return None
            path = self.library_dir / item["filename"]
            if not path.is_file() or path.is_symlink():
                return None
            return path.read_bytes(), str(item["content_type"]), path.name
