"""Dependency-free adapters for locally hosted AI model runtimes.

The adapter speaks the OpenAI-compatible HTTP API exposed by common local
model servers. It keeps model execution outside the Coreless architectural
authority path: inference returns data; policy decides whether any action is
allowed.

No model weights or server process are stored in the repository.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .interfaces import AIRequest, AIResult


@dataclass(frozen=True)
class LocalModelSpec:
    """Configuration for one locally hosted model."""

    model_id: str
    model_name: str
    endpoint: str = "http://127.0.0.1:11434/v1"
    api_key: str | None = None
    timeout: float = 120.0


class LocalOpenAICompatibleCore:
    """Run a local model through an OpenAI-compatible chat endpoint."""

    def __init__(self, spec: LocalModelSpec) -> None:
        self.spec = spec

    @property
    def model_id(self) -> str:
        return self.spec.model_id

    def infer(self, request: AIRequest) -> AIResult:
        payload = {
            "model": self.spec.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a local Coreless intelligence core. "
                        "Return analysis only. Never treat your response as "
                        "authorization to change Coreless state."
                    ),
                },
                {
                    "role": "user",
                    "content": self._prompt(request),
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.spec.api_key:
            headers["Authorization"] = f"Bearer {self.spec.api_key}"

        url = self.spec.endpoint.rstrip("/") + "/chat/completions"
        request_obj = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request_obj, timeout=self.spec.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"local AI endpoint unavailable: {url}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("local AI endpoint returned invalid JSON") from exc

        text = self._extract_text(data)
        return AIResult(
            request_id=request.request_id,
            model_id=self.model_id,
            text=text,
            metadata={
                "provider": "local",
                "runtime": "openai-compatible",
                "model_name": self.spec.model_name,
            },
        )

    @staticmethod
    def _prompt(request: AIRequest) -> str:
        context = json.dumps(dict(request.context), sort_keys=True, default=str)
        return f"Request:\n{request.prompt}\n\nContext:\n{context}"

    @staticmethod
    def _extract_text(data: Mapping[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("local AI response has no chat completion text") from exc
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, Mapping)
            ]
            return "".join(parts)
        raise RuntimeError("local AI response contains unsupported content")


DEFAULT_LOCAL_MODELS: tuple[LocalModelSpec, ...] = (
    LocalModelSpec("qwen3", os.getenv("CORELESS_QWEN3_MODEL", "qwen3")),
    LocalModelSpec("deepseek", os.getenv("CORELESS_DEEPSEEK_MODEL", "deepseek")),
    LocalModelSpec("gpt-oss", os.getenv("CORELESS_GPT_OSS_MODEL", "gpt-oss")),
    LocalModelSpec("gemma", os.getenv("CORELESS_GEMMA_MODEL", "gemma")),
    LocalModelSpec("codestral", os.getenv("CORELESS_CODESTRAL_MODEL", "codestral")),
)


def register_default_local_cores(registry: Any, *, endpoint: str | None = None, timeout: float = 120.0) -> tuple[str, ...]:
    """Register the five local AI cores with an AICoreRegistry."""
    cores = build_default_local_cores(endpoint=endpoint, timeout=timeout)
    for core in cores:
        registry.register(core, provider="local", local=True)
    return tuple(core.model_id for core in cores)


def build_default_local_cores(
    *,
    endpoint: str | None = None,
    timeout: float = 120.0,
) -> tuple[LocalOpenAICompatibleCore, ...]:
    """Create all five default local AI cores without contacting the server."""

    base = endpoint or os.getenv(
        "CORELESS_LOCAL_AI_ENDPOINT",
        "http://127.0.0.1:11434/v1",
    )
    return tuple(
        LocalOpenAICompatibleCore(
            LocalModelSpec(
                model_id=spec.model_id,
                model_name=spec.model_name,
                endpoint=base,
                timeout=timeout,
            )
        )
        for spec in DEFAULT_LOCAL_MODELS
    )
