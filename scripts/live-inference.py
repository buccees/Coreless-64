#!/usr/bin/env python3
"""Validate and exercise the five Coreless local AI cores against a live Ollama server.

This script performs no model installation. It only checks the running endpoint and
invokes the selected local models through the same 314DNest registry/coordinator
used by Coreless. Model weights remain outside the repository.
"""

from __future__ import annotations

import argparse
import os
import sys

from ai.coordinator import NestCoordinator
from ai.interfaces import AIRequest
from ai.registry import AICoreRegistry
from ai.local_runtime import register_default_local_cores


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live Coreless local AI inference")
    parser.add_argument(
        "--endpoint",
        default=os.getenv("CORELESS_LOCAL_AI_ENDPOINT", "http://127.0.0.1:11434/v1"),
    )
    parser.add_argument(
        "--prompt",
        default="Briefly describe how you would help diagnose a Coreless system resource issue.",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    registry = AICoreRegistry()
    register_default_local_cores(
        registry,
        endpoint=args.endpoint,
        timeout=args.timeout,
    )

    print("Coreless live inference")
    print(f"Endpoint: {args.endpoint}")
    print(f"Cores: {', '.join(registry.enabled_cores())}")
    print("Sending one request to all enabled local cores...")

    result = NestCoordinator(registry).coordinate(
        AIRequest(
            request_id="live-inference",
            prompt=args.prompt,
            context={"source": "coreless-live-validation"},
        )
    )

    for response in result.results:
        print(f"\n[{response.model_id}]")
        print(response.text)

    if result.failures:
        print("\nFailures:")
        for failure in result.failures:
            print(f"- {failure.model_id}: {failure.error_type}: {failure.message}")

    print("\n314DNest group result:")
    print(f"Participants: {', '.join(result.group.participants)}")
    print(f"Consensus: {result.group.recommended_action is not None}")
    print(f"Authorization required: {result.group.authorization_required}")

    return 0 if result.results else 1


if __name__ == "__main__":
    raise SystemExit(main())
