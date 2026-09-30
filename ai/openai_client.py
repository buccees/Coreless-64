"""Optional OpenAI Responses API adapter for Coreless.

This adapter is intentionally outside the Coreless CPU/ISA. It provides an
optional AI backend for development and the future Human-AI management plane.

Credentials are read only from the environment; never place an API key in
source control.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.6-luna"


class OpenAIConfigurationError(RuntimeError):
    """Raised when the optional OpenAI backend is not configured."""


class OpenAIRequestError(RuntimeError):
    """Raised when the OpenAI Responses API rejects a request."""


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_environment(cls) -> "OpenAIConfig":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY is not set; configure it before using the OpenAI backend"
            )
        return cls(
            api_key=api_key,
            model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            base_url=(
                os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
                or DEFAULT_BASE_URL
            ),
        )


class OpenAIResponsesClient:
    """Small standard-library client for the OpenAI Responses API."""

    def __init__(self, config: OpenAIConfig | None = None, timeout: float = 60.0):
        self.config = config or OpenAIConfig.from_environment()
        self.timeout = timeout

    def respond(self, text: str, *, store: bool = False) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        payload = {
            "model": self.config.model,
            "input": text,
            "store": bool(store),
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.base_url}/responses",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAIRequestError(
                f"OpenAI Responses API returned HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise OpenAIRequestError(f"OpenAI Responses API connection failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAIRequestError("OpenAI returned invalid JSON") from exc

        return _extract_text(data)


def _extract_text(response: dict) -> str:
    """Extract output text while tolerating the Responses API item structure."""
    direct = response.get("output_text")
    if isinstance(direct, str):
        return direct

    parts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)

    if parts:
        return "".join(parts)

    raise OpenAIRequestError("OpenAI response contained no text output")
