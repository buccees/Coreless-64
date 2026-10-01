# Coreless Roadmap

## Phase 1 — Architecture

- [x] Establish Coreless as the project name
- [x] Establish Coreless-64 as the first architecture
- [x] Define the independent-computer objective
- [x] Define the external environment as an interface
- [x] Define the machine / digital execution-engine distinction
- [x] Freeze CPU architectural state
- [x] Freeze instruction encoding and semantics
- [x] Freeze memory and address model
- [x] Freeze privilege and interrupt architecture
- [x] Freeze multiprocessing model
- [x] Freeze vector architecture
- [x] Freeze matrix/AI architecture
- [x] Freeze device and interconnect architecture
- [x] Freeze GPU/display architecture
- [x] Freeze virtualization architecture

## Phase 2 — Digital execution engine

Build the executable digital engine that runs the Coreless-64 machine.

The engine is part of the Coreless project. It provides the computational mechanism that makes the digital Coreless machine execute; it is not an external host dependency.

- [x] ISA decoder and instruction-length engine
- [x] CPU execution core
- [x] Memory system
- [x] Interrupt controller and timer foundation
- [x] Atomic execution
- [x] Persistent machine-state reference model
- [x] Storage-backed virtual RAM
- [x] Shared Coreless RAM across CPUs
- [x] Persist architectural CPU state
- [x] Network controller reference model
- [x] Virtual GPU/display reference model
- [x] Vector execution
- [x] Matrix/AI execution
- [x] Multiprocessing reference fabric
- [x] Virtualization reference model

## Phase 3 — Coreless operating environment

- [ ] Firmware
- [ ] Boot process
- [ ] Coreless kernel
- [ ] Process model
- [ ] Memory management
- [ ] Device drivers
- [ ] Networking
- [ ] GUI
- [ ] Remote display/input
- [ ] Application environment

## Phase 4 — Complete digital Coreless machine

Integrate the remaining machine subsystems into the same persistent execution model.

- [x] Persistent process and address-space state
- [x] Persistent operating-system state
- [x] Persistent device state
- [x] Persistent boot state
- [x] Persistent application state
- [x] Complete checkpoint/restore
- [x] Resume a complete Coreless machine from its machine image
- [ ] Run a complete Coreless operating environment through the digital execution engine

## Phase 5 — Portable Coreless machine

The target system is a portable computer whose digital machine travels with its persistent storage.

The external environment supplies power and I/O. The Coreless digital execution mechanism supplies the computation.

The Coreless architecture does not require a conventional host CPU, host OS, or host system RAM to be part of the Coreless computer.

## Static-Adaptive Model Parts

Coreless treats trained models as potential specialized computational parts rather than forcing every model into one generic Transformer implementation. A VM is the isolation/container "nest"; the model part retains its native architecture behind a Coreless model-part ABI.

- [x] Define ModelPart lifecycle and task contract
- [x] Define candidate → validating → active → retired adaptation lifecycle
- [x] Require validation before an adapted part can replace an active part
- [ ] Architecture-specific model-part execution (Qwen3, DeepSeek/R1, gpt-oss, Gemma, Codestral)
- [ ] Model-part ABI integration with VM IPC and capability control
- [ ] Task-driven automatic specialization planner
- [ ] User/workload-specific static adaptation state
- [ ] Slimline/pruning/quantization pipeline driven by retained task capability
- [ ] Specialized-part regression and acceptance suite
- [ ] Persistent adaptation history and rollback
- [ ] Continuous workload observation and adaptation triggers
- [x] Comprehensive compute/memory/storage/interconnect/network/media/external-I/O requirement envelope
- [ ] Automatic requirement discovery from installed devices and available I/O
- [ ] Market-generation capability profile updates without changing the Model-Part ABI

The intended lifecycle is:

**foundation training → released model → task specialization → slimline → validate → deploy as model part → observe workload → propose adaptation → validate → replace or rollback**

The specialization system must not constrain a model's native architecture merely to fit the VM. Architecture-specific execution is responsible for preserving model semantics; the model-part ABI defines the interface exposed to the rest of Coreless.

## AI-Derived Hardware Components

- [x] Define complete CPU hardware-role capability envelope
- [x] Define complete GPU hardware-role capability envelope
- [x] Define complete user-communication hardware-role capability envelope
- [x] Distinguish mandatory, retained-optional, and removable capabilities
- [x] Assign trained models to explicit Coreless hardware roles
- [x] Preserve each model's native architecture at the hardware boundary
- [x] Add validated model-part hardware execution endpoints
- [x] Add Coreless hardware-fabric request routing between model-parts
- [ ] Bind CPU model-part to the Coreless-64 instruction execution engine
- [ ] Bind GPU model-part to graphics/device/driver execution
- [ ] Bind communication model-part to the user session layer
- [ ] Add architecture-specific native execution adapters
- [ ] Validate real trained-model artifacts as hardware components

## 314DNest / Local Intelligence

- [x] AI-Core registry
- [x] Multi-model coordination
- [x] Deterministic collaboration/group result
- [x] Dynamic AI workload distribution and failover
- [x] Deterministic policy boundary
- [x] Capability-controlled Coreless resource operations
- [x] Telemetry
- [x] Audit records
- [x] Human-AI session layer
- [x] Structured terminal command ABI
- [x] Cancellation and bounded worker scheduling
- [x] Optional OpenAI development adapter
- [x] Local Qwen3 / DeepSeek / gpt-oss / Gemma / Codestral runtime adapters
- [x] AI compute fabric as a native machine resource
- [x] Unified conventional/AI scheduler with capacity and telemetry-aware allocation
- [x] Machine-level concurrent work distribution and fallback
- [x] Explicit AI compute capability advertisement
- [x] CorelessMachine unified work-distribution API
- [ ] Reproducible live Coreless test environment
- [ ] Live five-core inference on Coreless
- [x] Local tensor runtime foundation
- [x] Transformer execution foundation
- [ ] Model-format compatibility and real model-weight loading
- [ ] End-to-end local AI execution on Coreless resources

## Phase 6 — Scaling

- [ ] Dynamic CPU scaling
- [ ] Dynamic memory scaling
- [ ] Scalable vector resources
- [ ] Scalable AI resources
- [ ] Scalable GPU resources
- [ ] Large persistent machine images
- [ ] Multiple guest machines
- [ ] Multi-device Coreless systems

## Phase 7 — Compatibility

- [ ] Coreless-native toolchain
- [ ] x86-64 compatibility
- [ ] ARM64 compatibility
- [ ] Guest operating systems
- [ ] Binary translation
- [ ] Virtualized legacy environments

## Machine-state direction

The persistent machine image is becoming the authoritative carrier of Coreless machine state.

The target architecture is:

**power/startup → Coreless digital execution engine → Coreless machine → external I/O**

The machine image is intended to carry virtual RAM, CPU state, operating-system state, process state, device state, applications, filesystem state, and other state required to reconstruct the computer.

The current reference image still uses a simple object-based format. A later storage layer will replace this with a scalable sparse machine-image format suitable for very large virtual RAM and complete machine state.

## Execution-engine direction

The repository already contains the first digital Coreless execution engine.

reference/core.py implements Coreless-64 CPU instruction execution. reference/machine_runtime.py integrates those CPUs with shared Coreless memory, persistent storage, devices, graphics, networking, and machine-state persistence.

The next goal is not to replace that engine with an external runtime. The goal is to **complete its integration with the entire Coreless machine**, so the engine can execute a machine whose state is carried by its persistent machine image.

## Current status

The Coreless execution foundation and 314DNest management plane remain on the green baseline. The local model adapter and five-core registration are implemented. The current local-AI execution milestone is now the **reference tensor/Transformer path**: Coreless can execute token embeddings, causal attention, feed-forward layers, residual paths, normalization, and vocabulary logits using dependency-free Coreless tensors.

This is not yet live execution of Qwen3, DeepSeek, gpt-oss, Gemma, or Codestral weights. Model-format translation, real weight loading, tokenizer integration, and execution on an actual Coreless test environment remain separate tasks.

## Phase 1 status

The architectural definition is substantially complete. Coreless-64 defines CPU state, variable-length encoding, scalar/memory/atomic operations, virtual memory/MMU, privilege, interrupts, vector execution, matrix/AI execution, multiprocessing, device/interconnect principles, graphics/display, networking, virtualization, scaling, and security direction.

The remaining work before declaring a normative ISA v1.0 freeze is executable consistency testing, reserved-field audit, vector/matrix encoding cross-checks, and completion of implementation-heavy subsystem semantics.

## Phase 1 exit criteria

Before Coreless-64 is declared architecturally frozen, the project must pass a specification consistency audit covering instruction lengths, operand encodings, CSR numbering, exception causes, privilege transitions, page-table formats, memory ordering, vector/matrix restart semantics, device discovery, virtualization state, and capability discovery. The reference implementation must then execute conformance tests derived from the normative specification.
