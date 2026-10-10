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

See `REMAINING_REQUIREMENTS.md` for the consolidated remaining scope and completion gates. Also see `ROADMAP.md`, `TESTING.md`, `TEST_ENVIRONMENT.md`, `HANDOFF.md`, and the `specification/` directory for implementation status and normative contracts.

Do not commit model weights, API keys or credentials.


## Plug-and-play transport update — 2026-10-06

The reference host boundary now has a reusable transport-session layer in addition to identity and command framing. Coreless can enumerate a reference endpoint, verify its Coreless-64 identity, negotiate capabilities, bind channels, establish a `HostTransportSession`, exchange correlated command frames, and close the session without destroying Coreless machine state.

This is transport-neutral software infrastructure. It is intended to make the eventual USB, PCIe, network, storage-attached, and other adapters interoperable without moving CPU, RAM, OS, VM, AI, or architectural authority into the host.

The physical plug-and-play milestone remains open: cross-platform physical enumeration and concrete display/input/network transports are still to be implemented.


## Documentation checkpoint — 2026-10-06: scheduler and dispatch throughput

The latest green checkpoint is GitHub Actions **#1124**, commit `5df0639e70e4c7ada1143146d5121ec2731e93f5`. The preceding scheduler snapshot implementation exposed one incorrect empty-scheduler test expectation; that test was corrected to register a real resource and verify the scheduler-owned `(capacity, load)` snapshot. The implementation was unchanged by that correction.

The current throughput architecture now includes:

- scheduler-owned atomic resource state snapshots;
- eligible-capacity snapshots that preserve operation capability and AI model-affinity filtering;
- worker sizing from actual eligible capacity rather than total registered capacity;
- unified capacity accounting across parallel dispatch paths;
- direct single-item scheduler dispatch without thread-pool setup;
- deque-backed pending-work queues for constant-time admission;
- telemetry consumption from consistent scheduler resource state;
- preserved allocation, fallback, result-ordering, persistence, and AI authorization contracts.

This is an optimization layer over the existing Coreless machine architecture, not a change in computational authority. The scheduler remains the owner of resource allocation; AI remains a local machine resource and never becomes an authorization mechanism.


## Persistent runtime launcher — 2026-10-07

The repository now includes `scripts/coreless-run.py`, a direct launcher for a persistent Coreless machine image. It resumes the stored machine/OS state, accepts native Coreless shell commands, can advance the digital execution engine, and persists state or shutdown. The image remains the authoritative machine-state carrier and the host remains outside Coreless computational authority.


## Host transport hardening — 2026-10-08

The reference host transport now protects live reconnects from invalid replacement HostIO bundles and rejects closed raw socket channels before constructing a network transport. These boundaries are covered by green GitHub Actions runs through #1519. The transport layer remains transport-neutral above the socket adapter and does not claim physical display/input/network hardware implementation.


## Host transport hardening — 2026-10-08: transactional reconnects and session validation

The reference host transport now treats reconnect and HostIO channel binding as transactional operations. Failed replacement HostIO validation, identity attachment, channel rebinding, or partial HostIO binding no longer destroys an already-live attachment. Socket-backed reconnect failures also clean up replacement network transports without discarding the previous live session.

Reusable transport-session validation now detects closed raw sockets through the standard socket descriptor state as well as explicit transport `closed` properties. Regression coverage protects these lifecycle contracts.

Verified GitHub Actions runs **#1552** and **#1556** are green. This remains a transport-neutral host boundary; it does not claim completed physical display/input/network adapters or physical bus enumeration.


## Host transport checkpoint — 2026-10-08: session validation contract

Reusable host transport sessions distinguish session liveness from channel requirements: session validation checks attachment, identity, negotiated-state consistency, and closed channels that are present, while `require_channels()` explicitly rejects missing or closed requested channels. This keeps existing negotiated sessions compatible with partial channel binding while giving callers a deterministic completeness check when required.

GitHub Actions run **#1569** is green for the corrective validation checkpoint.


## Documentation checkpoint — 2026-10-08: socket transport hardening complete

The socket-backed host transport lifecycle hardening pass is complete at the reference boundary. Replacement socket construction failures now leave an existing live session intact; a later valid reconnect can recover normally. Send/receive transport failures retire the affected socket wrapper, cleanup errors do not mask the original transport failure, scoped cleanup preserves body exceptions, and disconnect detaches the Coreless interface even when socket cleanup reports an error.

Regression coverage exercises failed reconnect recovery, socket ownership across reconnects, closed-channel/session validation, transport retirement, and disconnect cleanup. **GitHub Actions run #1662 is green** for the final reconnect-recovery regression.

### Transport resume point

The reference socket lifecycle hardening is complete. Do not continue adding socket edge cases without a concrete contract failure. The next host-interface work is concrete cross-platform enumeration and platform display/input/network adapters.
