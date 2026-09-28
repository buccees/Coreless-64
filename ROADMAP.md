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
- [ ] Matrix/AI execution
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

## Phase 1 status

The architectural definition is substantially complete. Coreless-64 defines CPU state, variable-length encoding, scalar/memory/atomic operations, virtual memory/MMU, privilege, interrupts, vector execution, matrix/AI execution, multiprocessing, device/interconnect principles, graphics/display, networking, virtualization, scaling, and security direction.

The remaining work before declaring a normative ISA v1.0 freeze is executable consistency testing, reserved-field audit, vector/matrix encoding cross-checks, and completion of implementation-heavy subsystem semantics.

## Phase 1 exit criteria

Before Coreless-64 is declared architecturally frozen, the project must pass a specification consistency audit covering instruction lengths, operand encodings, CSR numbering, exception causes, privilege transitions, page-table formats, memory ordering, vector/matrix restart semantics, device discovery, virtualization state, and capability discovery. The reference implementation must then execute conformance tests derived from the normative specification.
