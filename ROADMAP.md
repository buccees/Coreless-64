# Coreless Roadmap

## Phase 1 — Architecture

- [x] Establish Coreless as the project name
- [x] Establish Coreless-64 as the first architecture
- [x] Define the independent-computer objective
- [x] Define the host as an external interface
- [x] Define the execution-model split between architecture and implementation
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

## Phase 2 — Reference execution

Build a software reference implementation of Coreless-64.

The reference implementation exists to validate the architecture. It is not the final computational dependency of Coreless.

- [x] ISA decoder and instruction-length reference engine
- [x] CPU execution core
- [x] Memory system
- [x] Interrupt controller and timer foundation
- [x] Atomic execution
- [x] Persistent machine-state reference model
- [x] Network controller reference model
- [x] Virtual GPU/display reference model
- [ ] Vector execution
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

## Phase 4 — Native execution

Investigate and prototype an execution substrate that does not depend on the host CPU for Coreless computation.

Potential paths:

- FPGA
- dedicated hardware
- accelerator
- ASIC
- storage-integrated execution
- heterogeneous execution

## Phase 5 — Portable Coreless machine

The target system is a portable computer in which the computational architecture travels with the device.

The host provides external interfaces rather than being the computer that executes Coreless.

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

## Phase 1 status

The architectural definition is substantially complete. Coreless-64 now defines CPU state, variable-length encoding, scalar/memory/atomic operations, virtual memory/MMU, privilege, interrupts, vector execution, matrix/AI execution, multiprocessing, device/interconnect principles, graphics/display, networking, virtualization, scaling, and security direction.

The remaining work before declaring a normative ISA v1.0 freeze is executable consistency testing, reserved-field audit, vector/matrix encoding cross-checks, and completion of implementation-heavy subsystem semantics.

## Phase 1 exit criteria

Before Coreless-64 is declared architecturally frozen, the project must pass a specification consistency audit covering instruction lengths, operand encodings, CSR numbering, exception causes, privilege transitions, page-table formats, memory ordering, vector/matrix restart semantics, device discovery, virtualization state, and capability discovery. The reference implementation must then execute conformance tests derived from the normative specification.

## Conformance layer

The reference layer now includes canonical instruction-boundary walking, extended-header decoding, malformed/truncated-instruction rejection, and base scalar encoding round-trip tests. This layer is now connected to an executable scalar reference core with architectural registers, precise retirement, CSR access, privilege checks, page translation, permission checks, and trap entry/return.

## Phase 2 implementation order

1. ISA decoder and instruction-length engine
2. Architectural register, privilege, CSR, and precise-trap state
3. MMU and page-table walker
4. Scalar/memory execution
5. Atomic execution
6. Interrupt and timer controller
7. Vector execution
8. Matrix/AI execution
9. Multiprocessor scheduler and shared-memory model
10. Device and DMA model
11. Storage and persistent machine state
12. Network and graphics subsystems
13. Virtualization
14. Coreless operating environment

## Architecture audit findings

Phase 1 is substantially specified but is not yet formally frozen. The audit gaps in CSR numbering, page-table format, exception causes, reset state, capability discovery, device discovery, interrupt entry/return state, and extended-instruction field assignments have now been concretized. Remaining review is focused on executable cross-checks and implementation-heavy semantics.
