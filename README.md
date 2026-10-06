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

The repository is at the current implementation checkpoint; CI status is tracked by GitHub Actions rather than frozen in this document.

Latest confirmed integration commit:
`e3ee0676e6045963e1004940326730ed4af7a067`

The current implementation includes:
- Coreless-64 ISA and variable-length instruction framing
- CPU, memory, privilege, interrupts, atomics, vector and matrix execution
- multiprocessing, persistent storage, virtual RAM, devices, graphics/network foundations
- VM isolation, IPC, shared-memory capability control and hypervisor lifecycle
- firmware, boot, reference OS/process/memory lifecycle
- checkpoint/restore and machine resume
- coordinated Hub checkpoint commit verification with failed-publication manifest rollback
- 314DNest coordination, policy, capabilities, telemetry, audit and sessions
- persistent Coreless TensorRuntime
- native vector add/multiply and deterministic vector dot
- supported-shape native integer matrix execution
- TensorRuntime scalar broadcast and transpose primitives
- Coreless-native RMSNorm, reciprocal/rsqrt, rotary trig, masking, scalar scaling, and deterministic argmax boundaries
- Transformer execution routed through TensorRuntime
- Qwen3 runtime with GQA, KV cache, rotary attention, RMSNorm, SwiGLU, generation, and progressively deeper TensorRuntime execution
- autonomous Coreless component identity, specialization, hub discovery, connect/disconnect, composition metadata, fault isolation, capability-routed workload dispatch, and native CPU/VM execution

**Important:** green CI is not proof of live trained-model inference. Official trained Qwen3-0.6B end-to-end execution remains unvalidated.

## Plug-and-play computer interface

Coreless now treats the host connection as a narrow external interface: power/startup, display transport, keyboard/input transport, and network/I/O transport. The host does not supply Coreless CPU, RAM, OS execution, VM execution, AI computation, or architectural authority.

The target plug-and-play lifecycle is: **connect → discover → verify Coreless identity → advertise capabilities → negotiate interfaces → attach → boot/resume → operate → detach**.

The normative target is documented in `specification/host_interface.md`. The reference host transport adapter and channel-binding contract are implemented; physical cross-platform enumeration and concrete display/input/network transports remain open.

## Next engineering checkpoint

1. **Autonomous component system:** complete unified Hub lifecycle and native CPU/VM execution across standalone and composed components.
2. **Plug-and-play host interface:** extend the reference transport adapter toward concrete display/input/network transports and cross-platform enumeration.
3. **Deep Qwen3/Coreless tensor boundary:** move remaining KV-cache, head reshape/repeat, masking, and attention data movement into TensorRuntime without weakening the architectural boundary.
4. Validate a real official trained Qwen3-0.6B artifact with a minimal forward pass and short generation.
5. Extend native model runtimes and bind validated model parts to live Coreless resources.
6. Complete final ISA, persistence, capability, AI-control, host-interface, and end-to-end conformance audit.

## 314DNest

314DNest is the local System Fabric coordinating AI cores with Coreless resources. AI output is never authorization:

**AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit**

Qwen3, DeepSeek, gpt-oss, Gemma and Codestral remain local model participants; GPT-5.6 Luna is optional through the OpenAI development adapter.

## Documentation

See `ROADMAP.md`, `TESTING.md`, `TEST_ENVIRONMENT.md`, `HANDOFF.md`, and the `specification/` directory for the current project record.

Do not commit model weights, API keys or credentials.
