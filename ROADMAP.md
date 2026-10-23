# Coreless Roadmap

## Portability and hardware-identity goals

**The SSD holds the whole Coreless-64 machine, including its execution engine, OS/environment, configuration, and persistent state.** The OS runs on that machine. Lubuntu is the user's preferred OS for initial bring-up, not a host OS that owns Coreless execution. Keep the machine architecture, boot path, device model, and OS/runtime authority distinct from the chosen operating system. The portability goal is to boot and operate the Coreless machine from a broad range of supported SSDs and to expose Coreless's own identity through suitable hardware interfaces. The engineering goal is the complete SSD-carried machine, not a program installed on a host. Validate its execution/boot path and required physical interfaces against that architecture.

The portability goal includes USB-attached SATA/NVMe SSDs and native SATA/NVMe storage where the host firmware, bus, drivers, and boot path support them. Do not claim universal SSD compatibility without a tested drive/host/interface matrix.

Keep three concepts distinct: storage enclosure/controller identity, persistent Coreless machine identity, and optional hardware-level device identity exposed to another host. A normal external SSD cannot become a separate USB computer solely because Coreless software is stored on it. A distinct device-mode/composite interface requires compatible device-side controller hardware, firmware, transport implementation, and host-side validation; USB gadget/device mode is a hardware-dependent possibility, not a universal feature.

## Current checkpoint

The current implementation checkpoint includes the reference digital-machine lifecycle, persistent TensorRuntime, native vector/matrix execution foundations, Transformer → TensorRuntime routing, autonomous Coreless components, Hub composition, coordinated persistence, native CPU/VM component execution, Hub scheduling, a reference plug-and-play host transport layer, and an authenticated read-only Remote Operator Display endpoint backed by the active CorelessSystem. This operator surface reports runtime lifecycle and only those sensor events explicitly supplied to its telemetry provider; it does not imply physical sensor connectivity or a complete in-machine GUI.

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
- [x] Authenticated read-only remote operator display page and runtime-state endpoint (reference implementation)
- [ ] Complete in-machine GUI and platform-specific display/input transports
- [x] User-designated pointing-device subsystem
- [x] Touch/pointing input routing through Coreless input boundary
- [x] Initial optional VIGIL input interpretation layer
- [x] Plug-and-play host discovery and identity handshake software contract
- [x] Host capability negotiation and attach/detach software contract
- [x] Reference host enumeration/transport adapter
- [x] Provider-backed host transport adapter boundary
- [x] Transport-neutral host hot-plug lifecycle coordinator (software contract only)
- [ ] First native host adapter on Lubuntu/Linux: device-event subscription (evaluate udev/libudev) and arrival/removal handling
- [ ] Physical unplug/replug and reconnect validation on the first Lubuntu test host
- [ ] End-to-end VIGIL integration with native hot-plug lifecycle
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

- [ ] Validate the Coreless execution engine → machine boot → operating-system startup path as one integrated lifecycle
- [ ] Define and validate the boot contract so the OS runs on the Coreless execution engine and retains machine-level authority

- [ ] Define a storage compatibility matrix (USB-attached SATA SSD, USB-attached NVMe SSD, native SATA, native NVMe; include boot firmware/driver constraints)
- [ ] Test persistent Coreless machine portability across multiple SSDs and host computers without assuming storage identity equals Coreless machine identity
- [ ] Specify hardware-level Coreless device identity separately from storage/enclosure identity
- [ ] Evaluate distinct USB/device-mode enumeration on compatible hardware; document required controller/firmware and test host interoperability before claiming support

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
- [ ] Validate physical host enumeration on Lubuntu/Linux, then add tested providers for other supported host OSes
- [x] Reference display/input/network transport adapters
- [ ] Validate display/input/network transport adapters on Lubuntu/Linux, then add other OS adapters
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

## Current blocker — VIGIL hot-plug unavailable

VIGIL **cannot use hot-plug yet**. The transport-neutral `HostHotplugController` exists and has software lifecycle tests, but it does not detect physical device events by itself. Native OS/device event subscriptions, concrete platform transport teardown/reopen, real unplug/replug validation, and an end-to-end VIGIL integration test remain incomplete. Do not describe VIGIL hot-plug as available until those checkpoints pass. This is a recorded blocker only; VIGIL spatial-intelligence expansion remains paused.

## Resume point

**Current next priorities:** implement and validate concrete platform host enumeration and display/input/network transport adapters; validate the existing authenticated Remote Operator Display against the active machine lifecycle and observed VIGIL event ledger without fabricating sensor state; then continue deeper native Coreless execution and official trained Qwen3-0.6B end-to-end validation. The VIGIL spatial-intelligence expansion is paused; its existing research notes and historical decisions remain preserved.


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

The existing implementation provides the Qwen3 KV-cache/head-data **software boundary** through TensorRuntime-backed append/persistence, head reshape/repeat, grouped attention, and focused regression coverage. Code reviewed on 2026-10-22 in `ai/qwen3.py`, `ai/tensor_runtime.py`, `ai/test_qwen3.py`, and `ai/test_tensor_runtime.py` confirms this checklist item is complete; do not reopen it as missing implementation. Scope limit: Tensor payloads still use Python numeric tuples, and several runtime operations execute Python-level loops/fallbacks, so this is not proof of hardware-native data movement or trained-model end-to-end inference. Open checkpoints remain: deeper native Coreless execution and performance validation, concrete host transport adapters, and official trained Qwen3-0.6B end-to-end validation.


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
