# Coreless Testing

# 🚧 **LIVE TEST ENVIRONMENT REQUIRED**

**The repository cannot perform live Coreless inference until an actual Coreless test environment exists.**

GitHub CI validates the reference implementation and its deterministic components. It does **not** prove that the complete Coreless computer can boot/run as the intended persistent-storage-hosted environment, nor does it provide the local model weights needed for live AI inference.

## Current status

- Reference implementation: available
- CI/reference tests: available
- 314DNest coordination: available
- Local AI adapters: available
- Live inference runner: available
- **Actual Coreless runtime test environment: NOT YET AVAILABLE**
- Live five-model inference: **BLOCKED until the test environment exists**

## Test environment requirements

The test environment needs:

1. Persistent storage containing the Coreless environment.
2. A way to start the current Coreless execution engine.
3. Required display/input/network interfaces for the current runtime.
4. Python and the Coreless repository.
5. A local AI runtime such as Ollama exposing an OpenAI-compatible endpoint.
6. The configured local models:
   - Qwen3
   - DeepSeek
   - gpt-oss
   - Gemma
   - Codestral

Model weights should remain outside Git.

## Live inference validation

After the environment is available:

```bash
python3 scripts/live-inference.py
```

Expected validation flow:

```
Coreless runtime
      ↓
314DNest
      ↓
AI-Core Registry
      ↓
Qwen3 / DeepSeek / gpt-oss / Gemma / Codestral
      ↓
live responses
      ↓
314DNest group result
      ↓
deterministic policy boundary
```

A model response is never authorization to modify protected Coreless state.

## What comes next

The immediate infrastructure task is to establish a **repeatable Coreless test environment** that another developer can reproduce. Once that exists, live inference can be tested against the real runtime rather than mocked CI endpoints.

Do not mark live inference complete based solely on CI.
