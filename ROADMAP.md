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
- [ ] Tensor-backed Qwen3 KV cache and native head reshape/repeat/data-movement boundary
- [ ] Actual persistent-storage-hosted Coreless runtime environment
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
- [x] Qwen3 KV cache
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
- [ ] Concrete display/input/network transport adapters
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
