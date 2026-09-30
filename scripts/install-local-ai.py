#!/usr/bin/env python3
"""Prepare the Coreless local-AI configuration.

This script deliberately does not download model weights. Model servers and
weights are runtime/environment concerns, while Coreless owns the AI-Core
interface and policy boundary.

For a local OpenAI-compatible server, set CORELESS_LOCAL_AI_ENDPOINT and the
five CORELESS_*_MODEL variables if its model names differ from the defaults.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.local-ai.example"


def main() -> None:
    endpoint = os.getenv(
        "CORELESS_LOCAL_AI_ENDPOINT",
        "http://127.0.0.1:11434/v1",
    )
    content = f"""# Coreless local AI runtime
CORELESS_LOCAL_AI_ENDPOINT={endpoint}
CORELESS_QWEN3_MODEL={os.getenv("CORELESS_QWEN3_MODEL", "qwen3")}
CORELESS_DEEPSEEK_MODEL={os.getenv("CORELESS_DEEPSEEK_MODEL", "deepseek")}
CORELESS_GPT_OSS_MODEL={os.getenv("CORELESS_GPT_OSS_MODEL", "gpt-oss")}
CORELESS_GEMMA_MODEL={os.getenv("CORELESS_GEMMA_MODEL", "gemma")}
CORELESS_CODESTRAL_MODEL={os.getenv("CORELESS_CODESTRAL_MODEL", "codestral")}
"""
    ENV_EXAMPLE.write_text(content, encoding="utf-8")
    print(f"Wrote {ENV_EXAMPLE}")
    print("Start an OpenAI-compatible local model server, then use these settings.")
    print("No API key is required by the Coreless local adapter unless your local server requires one.")


if __name__ == "__main__":
    main()
