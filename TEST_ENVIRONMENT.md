# Coreless Test Environment

# 🚧 **THIS IS THE REPRODUCIBLE CORELESS TEST ENVIRONMENT TRACK**

The test environment is part of Coreless, not a side project. It exists so another developer can reproduce a developer-side execution environment and eventually execute the complete persistent-storage-hosted computer.

## Phase 1 — Prepare

```bash
bash scripts/bootstrap-test-environment.sh
source .coreless-venv/bin/activate
```

This creates an isolated Python environment and installs repository requirements when present. It does not download model weights or replace the host operating system.

## Phase 2 — Reference validation

```bash
python -m pytest
```

## Phase 3 — Local intelligence

```bash
python3 scripts/install-local-ai.py --pull
```

Model weights remain outside Git.

## Phase 4 — Live five-core inference

With the local runtime running:

```bash
python3 scripts/live-inference.py
```

This exercises Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral through 314DNest.

## Phase 5 — Full Coreless execution target

The remaining environment milestone is a reproducible way to start the Coreless execution engine itself from persistent storage, with virtual CPUs, virtual memory, storage, devices, and System Fabric operating together.

That is distinct from ordinary Python test execution and must be validated separately.

## Parallel development

The environment track does not stop Coreless architecture development. Tensor runtime, vector/matrix execution, Transformer compatibility, native Coreless OS/runtime, ISA/conformance, and 314DNest integration continue in parallel.
