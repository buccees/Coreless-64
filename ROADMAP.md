# Coreless Roadmap

## Current checkpoint

The current implementation checkpoint includes the complete reference digital-machine lifecycle, persistent TensorRuntime, native vector/matrix execution foundations, Transformer → TensorRuntime routing, autonomous Coreless components, Hub composition, coordinated persistence, native CPU/VM component execution, Hub scheduling, and a reference plug-and-play host transport layer.

## Phase 1 — Architecture

- [x] Coreless-64 architecture and independent-computer objective
- [x] CPU architectural state
- [x] Variable-length instruction encoding
- [x] Memory/address model
- [x] Privilege/interrupt architecture
- [x] Multiprocessing
- [x] Vector architecture
- [x] Matrix/AI architecture
- [x] Device/interconnect architecture
- [x] Autonomous component/hub architecture
- [x] Plug-and-play host boundary specification
- [x] Graphics/display architecture
- [x] Virtualization architecture
- [ ] Final specification consistency audit and normative v1.0 freeze

## Phase 2 — Digital execution engine

- [x] ISA decoder/instruction-length engine
- [x] CPU execution core
- [x] Memory system
- [x] Interrupt/timer foundation
- [x] Atomic execution
- [x] Persistent machine state
- [x] Storage-backed virtual RAM
- [x] Shared RAM across CPUs
- [x] Persistent CPU state
- [x] Network controller reference model
- [x] Virtual GPU/display model
- [x] Vector execution
- [x] Matrix/AI execution
- [x] Multiprocessing fabric
- [x] Virtualization model

## Phase 3 — Coreless operating environment

- [x] Firmware
- [x] Boot
- [x] Reference Coreless OS runtime
- [x] Process model
- [x] Memory management
- [ ] Device drivers
- [ ] Networking
- [ ] GUI
- [ ] Remote display/input
- [x] User-designated pointing-device subsystem
- [x] Touch/pointing input routing through Coreless input boundary
- [x] Initial optional VIGIL input interpretation layer
- [x] Plug-and-play host discovery and identity handshake software contract
- [x] Host capability negotiation and attach/detach software contract
- [x] Reference host enumeration/transport adapter
- [x] Provider-backed host transport adapter boundary
- [ ] Application environment

## Phase 4 — Complete digital machine

- [x] Persistent process/address-space state
- [x] Persistent OS/device/boot/application state
- [x] Checkpoint/restore
- [x] Coordinated Hub checkpoint commit verification and failed-commit manifest rollback
- [x] Resume from machine image
- [x] Complete reference lifecycle through the digital execution engine
- [x] Autonomous component execution boundary
- [x] Hub workload routing and parallel dispatch
- [x] Native CPU/VM execution for component VMs
- [x] Hub multi-vCPU scheduling

## Phase 5 — Portable Coreless machine

- [x] Reproducible digital/reference test environment
- [x] Complete reference machine lifecycle
- [x] Persistent TensorRuntime
- [x] Transformer execution through TensorRuntime
- [x] Stable native Coreless execution boundary for Transformer tensor operations
- [x] TensorRuntime RMSNorm, scalar broadcast, and transpose primitives
- [x] Qwen3 rotary/masking/scalar-scale/argmax paths routed through TensorRuntime
- [x] TensorRuntime-backed Qwen3 KV-cache storage and native head reshape/repeat/data-movement boundary
- [x] Actual persistent-storage-hosted Coreless runtime environment
- [ ] Live five-core inference on Coreless
- [ ] End-to-end local AI execution on Coreless resources

## Static-Adaptive Model Parts

- [x] ModelPart lifecycle/task contract
- [x] Candidate → validating → active → retired lifecycle
- [x] Validation before replacement
- [ ] Architecture-specific native execution for Qwen3, DeepSeek/R1, gpt-oss, Gemma, Codestral
- [ ] Model-part ABI/VM IPC/capability integration
- [ ] Specialization planner
- [ ] User/workload adaptation state
- [ ] Slimming/pruning/quantization
- [ ] Regression/acceptance suite
- [ ] Adaptation history/rollback
- [ ] Continuous workload adaptation triggers

## AI-Derived Hardware Components

- [x] Storage-backed safetensors
- [x] Native Qwen3 artifact validation/loading
- [x] Native Qwen3 tokenizer/greedy generation
- [x] Qwen3 KV cache generation/layout
- [x] Qwen3 grouped-query attention cache layout and generation path
- [x] Real artifact integration runner
- [ ] Official trained Qwen3-0.6B end-to-end validation
- [x] CPU/GPU/communication capability envelopes
- [x] Explicit hardware-role assignment
- [x] Native architecture preservation
- [x] Model-part execution endpoints and fabric routing
- [ ] Bind CPU model part to Coreless-64 instruction execution
- [ ] Bind GPU model part to graphics/device/driver execution
- [ ] Bind communication model part to user session layer
- [ ] Native architecture adapters
- [ ] Live trained model components

## 314DNest / Local Intelligence

- [x] AI-Core registry
- [x] Multi-model coordination
- [x] Deterministic group result
- [x] Dynamic workload distribution/failover
- [x] Deterministic policy boundary
- [x] Capability-controlled Coreless resources
- [x] Telemetry/audit
- [x] Human-AI sessions
- [x] Structured terminal ABI
- [x] Cancellation/bounded workers
- [x] Optional OpenAI adapter
- [x] Local model runtime adapters
- [x] Native AI compute resource/scheduler
- [x] Unified machine work-distribution API
- [x] Digital/reference test environment
- [x] Local TensorRuntime foundation
- [x] Transformer execution foundation
- [x] Model-format/loading foundation
- [x] Native Coreless execution boundary
- [ ] Live five-core inference
- [ ] End-to-end local AI on Coreless resources

## Phase 6 — Scaling

- [ ] Dynamic CPU/memory/vector/AI/GPU scaling
- [ ] Large persistent machine images
- [ ] Multiple guest machines
- [ ] Multi-device Coreless systems
- [ ] Autonomous component hot-plug across Coreless Hubs

## Phase 7 — Compatibility

- [ ] Coreless-native toolchain
- [ ] x86-64 compatibility
- [ ] ARM64 compatibility
- [ ] Guest operating systems
- [ ] Binary translation
- [ ] Legacy virtualization

## Plug-and-play host interface

- [x] Host boundary defined as external I/O, not Coreless computation
- [x] Identity/discovery requirements documented
- [x] Capability negotiation requirements documented
- [x] Component/hub composition boundary documented
- [x] CorelessHostInterface software contract
- [x] Reference host enumeration/transport adapter
- [ ] Cross-platform physical host enumeration
- [x] Reference display/input/network transport adapters
- [ ] Platform display/input/network transport adapters
- [x] User-designated pointing-device discovery and persistent assignment
- [x] Coreless touch/pointing event transport contract
- [x] VIGIL-aware input interpretation boundary
- [x] Input-device failover and reassignment

## VIGIL input integration

The Coreless input architecture uses VIGIL as an optional interpretation layer. VIGIL is now contained in the Coreless repository rather than being a separate runtime dependency.

- [x] Define Coreless input event ABI for pointer, touch, stylus, and gesture events
- [x] Define user designation and persistent identity for a primary pointing device
- [x] Define device discovery, capability advertisement, assignment, reassignment, and failover
- [x] Route designated pointing-device events through the Coreless input boundary
- [x] Define initial VIGIL interpretation API and capability boundary
- [ ] Implement gesture and multi-touch interpretation through VIGIL
- [x] Preserve raw-event access for applications that do not use VIGIL
- [x] Keep VIGIL optional so basic pointer/touch operation does not depend on VIGIL
- [x] Add deterministic input regression/acceptance tests
- [x] Integrate VIGIL input state with persistent Coreless machine state where appropriate
- [x] Add optional camera-frame ingestion boundary
- [ ] Implement camera perception/tracking
- [ ] Implement camera-based pointing
- [ ] Implement spatial gesture recognition
- [ ] Implement VIGIL spatial/world-model services inside Coreless

## Resume point

**Next:** deepen the Coreless/Qwen3 execution boundary with tensor-backed KV-cache and native head data movement, while continuing concrete plug-and-play host transports → trained Qwen3-0.6B validation → persistent-storage-hosted runtime → live Coreless inference. Continue the optional VIGIL camera/spatial layer in parallel.


## Latest transport milestone

The reference plug-and-play boundary now includes reusable transport sessions above identity and command framing.

- [x] Transport-neutral Coreless identity frame
- [x] Correlated device command/response frame
- [x] Reference host endpoint enumeration
- [x] Capability negotiation and channel binding
- [x] Reusable host transport session
- [x] Session command exchange and correlated responses
- [x] Session close preserving Coreless machine state
- [ ] Cross-platform physical host enumeration
- [ ] Concrete display/input/network transport adapters


## Documentation checkpoint — 2026-10-06: scheduler and dispatch throughput

The latest documented scheduler milestone was GitHub Actions **#1124**, commit `5df0639e70e4c7ada1143146d5121ec2731e93f5`. The current verified green repository checkpoint is GitHub Actions **#1244**, commit `674ea90b251fdad141b338be880b644b21d89113`. The preceding scheduler snapshot implementation exposed one incorrect empty-scheduler test expectation; that test was corrected to register a real resource and verify the scheduler-owned `(capacity, load)` snapshot. The implementation was unchanged by that correction.

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

### Throughput architecture milestone

- [x] Scheduler-owned atomic resource state snapshots
- [x] Eligible-capacity dispatch accounting
- [x] AI model-affinity-aware concurrency sizing
- [x] Single-item scheduler fast path
- [x] Deque-backed pending dispatch queue
- [x] Unified scheduler capacity accounting
- [x] Telemetry/resource-state hot-path optimization


## Documentation checkpoint — 2026-10-07: Qwen3 tensor boundary verified

The existing implementation already provides TensorRuntime-backed Qwen3 KV-cache append/persistence plus native head reshape, repeat, grouped-attention movement, and regression coverage. This roadmap item is now recorded as complete. The next implementation priority is concrete host transport adapters and persistent-storage-hosted execution; official trained Qwen3-0.6B validation remains deferred until that boundary is stable.


## Documentation checkpoint — 2026-10-07: persistent runtime launcher

The persistent-storage-hosted reference runtime now has a direct launcher at `scripts/coreless-run.py`. It opens the Coreless machine image as the authoritative state carrier, resumes the Coreless OS/runtime, accepts native Coreless shell commands, optionally advances the digital execution engine, and persists shutdown/state without moving computational authority into the host. Lifecycle regression coverage is in `reference/test_persistent_runtime.py`.


## Documentation checkpoint — 2026-10-07: reference host I/O integration

The host transport milestone has advanced from negotiated channels to an end-to-end reference I/O path. The Coreless host boundary can now bind a persistent Coreless system to concrete in-memory display, input, and network transports. Input events are serialized into the host channel and decoded back into the Coreless input ABI; display scanout frames can be emitted to the host display transport; and network packets can cross the host boundary in both directions.

Verified CI runs include #1314 (end-to-end host I/O integration) and #1315 (clean host I/O reconnect handling), both green. The remaining host-interface work is platform-specific enumeration and transport adapters.


## Documentation checkpoint — 2026-10-07: platform-independent host discovery

The reference host boundary now has a dedicated platform-independent discovery layer in `reference/host_discovery.py`. `HostDeviceEnumerator` accepts raw transport-neutral identity advertisements from concrete adapters, validates Coreless-64 identity/protocol data, derives device capabilities from the advertisement, and returns deterministically ordered `HostEndpoint` objects. Duplicate endpoint IDs and malformed identity frames are rejected before attachment.

This separates transport-neutral Coreless discovery from future OS/device-specific enumeration. Physical USB, PCIe, Ethernet, SATA, NVMe, display, input, and network adapters remain outside this layer and must continue to use the same discovery contract.


## Documentation checkpoint — 2026-10-07: HostIO transport boundary

The host transport layer now validates the transport-neutral HostIO bundle before endpoint attachment, and HostTransportAdapter.open_session() carries the same explicit HostIO contract. Invalid host I/O bundles are rejected before Coreless attachment state changes. This completes the reference software boundary for negotiated display/input/network I/O; physical OS/device enumeration and platform-specific transport adapters remain intentionally separate implementation work.

- [x] Transport-neutral HostIO channel contracts
- [x] Transport-neutral HostIO bundle contract
- [x] HostIO bundle validation at the Coreless boundary
- [x] HostIO bundle validation at the transport connection boundary
- [x] HostIO-aware reusable transport sessions
- [ ] Cross-platform physical host enumeration
- [ ] Platform display/input/network transport adapters


## Documentation checkpoint — 2026-10-07: atomic HostIO validation

- [x] Validate the complete negotiated HostIO bundle before attachment
- [x] Validate the Coreless input-router contract before binding
- [x] Preserve no-partial-attachment behavior on HostIO validation failure

The reference test suite is green at this checkpoint. Next implementation work should proceed toward concrete platform host providers/adapters while preserving the transport-neutral boundary.


## Documentation checkpoint — 2026-10-08: reconnect transaction hardening

- [x] Reject already-closed raw socket channels at adapter construction
- [x] Clean up newly constructed socket transports on failed connection
- [x] Preserve a live attachment when replacement HostIO validation fails
- [x] Cover reconnect HostIO atomicity with regression tests

The latest transport-hardening reference tests are green. The next implementation step should address the next concrete transport lifecycle contract without regressing the transport-neutral HostIO/discovery boundaries.


## Documentation checkpoint — 2026-10-08: transactional transport/session hardening

- [x] Validate replacement HostIO before reconnect mutation
- [x] Roll back host identity attachment state on failed reconnect
- [x] Preserve a live session across failed transport channel rebinding
- [x] Roll back partial HostIO channel binding
- [x] Clean up failed replacement socket network transports
- [x] Reject closed raw sockets at adapter and session validation boundaries
- [x] Cover reconnect and closed-session lifecycle contracts with regression tests

The latest transport-hardening fixes are green in GitHub Actions through runs **#1552** and **#1556**. The next implementation step should move to the next concrete transport lifecycle/provider contract while preserving the transport-neutral HostIO, discovery, command, and session boundaries.



## Documentation checkpoint — 2026-10-08: session validation contract correction

- [x] Keep reusable-session validation focused on attachment/identity/negotiation/liveness
- [x] Require explicit channel completeness through `require_channels()`
- [x] Cover missing required session channels with regression coverage
- [x] Reject closed raw sockets consistently at session validation boundaries

GitHub Actions **#1569** is green on the corrective session-validation commit. The next implementation step is the next concrete socket/transport lifecycle or platform-provider contract; do not broaden `validate()` into an implicit channel-completeness check.
