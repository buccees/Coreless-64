# Coreless

[**Coreless-64 album cover artwork — Claude**](./Coreless-64%20album%20cover%20artwork%20-%20Claude.html)

**Coreless is a computer architecture in which the complete digital computer can be carried by persistent storage and executed by a digital Coreless execution engine.**

> **Coreless is the computer. Persistent storage carries the machine state. The Coreless digital execution engine runs the machine. External equipment provides power and I/O.**

## Coreless-64

Coreless-64 is the 64-bit Coreless architecture. The repository contains its digital reference execution engine, persistent machine model, operating-environment foundation, virtualization, devices, vector/matrix execution, and 314DNest local-intelligence layer.

Persistent storage is the authoritative carrier of machine state. The external environment is an I/O boundary, not the computational owner of Coreless.

## Autonomous component architecture

Coreless is also designed as a **composable computer made of autonomous Coreless components**.

Each component is intended to be a complete Coreless unit rather than a passive peripheral. A component can carry its own execution, memory/storage, VM boundary, AI runtime/model, role specialization, and communication identity.

Components therefore support two modes:

- **Standalone:** a component can operate independently.
- **Unified:** multiple components can connect through a Coreless Hub and form a larger Coreless computer.

A component retains its identity and specialization when connected. Disconnecting it must leave it capable of independent operation, and reconnecting it must allow discovery and composition again.

Per-component AI is part of this architecture. Models can specialize around the role of their component, with training/adaptation occurring inside the component VM where appropriate. Coreless architectural, VM, capability, and policy controls remain authoritative.

The initial software boundary is implemented in `reference/components.py` and specified in `specification/component_architecture.md`.

## Current status

**GREEN — GitHub Actions run #423 succeeded.**

Latest confirmed integration commit:
`aabd6c177d902b836aad85bda399a73df9fbd659`

The current implementation includes:
- Coreless-64 ISA and variable-length instruction framing
- CPU, memory, privilege, interrupts, atomics, vector and matrix execution
- multiprocessing, persistent storage, virtual RAM, devices, graphics/network foundations
- VM isolation, IPC, shared-memory capability control and hypervisor lifecycle
- firmware, boot, reference OS/process/memory lifecycle
- checkpoint/restore and machine resume
- 314DNest coordination, policy, capabilities, telemetry, audit and sessions
- persistent Coreless TensorRuntime
- native vector add/multiply and deterministic vector dot
- supported-shape native integer matrix execution
- Transformer execution routed through TensorRuntime
- native Qwen3 runtime foundations, tokenizer, KV cache, artifact validation and generation path
- autonomous Coreless component identity, specialization, hub discovery, connect/disconnect, and composition metadata

**Important:** green CI is not proof of live trained-model inference. Official trained Qwen3-0.6B end-to-end execution remains unvalidated.

## Next engineering checkpoint

1. **Native Coreless execution boundary:** establish/stabilize a public architectural vector/matrix API and route supported Transformer operations through it.
2. **Autonomous component foundation:** bind components to complete CorelessSystem instances, persist identity/specialization, and add VM/AI lifecycle ownership.
3. Validate a real official trained Qwen3-0.6B artifact with a minimal forward pass and short generation.
4. Extend native model runtimes and bind validated model parts to live Coreless resources.
5. Continue drivers, networking, GUI, remote display/input and application environment.
6. Complete final ISA, persistence, capability, AI-control and end-to-end conformance audit.

## 314DNest

314DNest is the local System Fabric coordinating AI cores with Coreless resources. AI output is never authorization:

**AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit**

Qwen3, DeepSeek, gpt-oss, Gemma and Codestral remain local model participants; GPT-5.6 Luna is optional through the OpenAI development adapter.

## Documentation

See `ROADMAP.md`, `TESTING.md`, `TEST_ENVIRONMENT.md`, `HANDOFF.md`, and the `specification/` directory for the current project record.

Do not commit model weights, API keys or credentials.
