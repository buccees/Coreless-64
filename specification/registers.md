# Coreless-64 Registers

**Version:** 0.1  
**Status:** Draft

## General-purpose registers

Coreless-64 defines 32 general-purpose 64-bit registers: R0 through R31.

All 32 are architecturally addressable by scalar instructions.

The software ABI will assign conventional roles for arguments, return values, temporaries, saved registers, stack pointer, frame pointer, and thread pointer without unnecessarily hard-coding those roles into the ISA.

## Program counter

PC is a dedicated 64-bit program counter.

## Stack pointer

SP is a dedicated 64-bit architectural stack pointer.

## Control state

Privileged control state will contain privilege, interrupt, exception, translation, arithmetic-status, and execution-control state. Detailed system-register encoding belongs in privilege.md.

## Vector registers

Coreless-64 will provide 32 scalable vector registers.

The architectural vector length is independent of one fixed physical vector width. The vector architecture will support masking/predication and element types from 8-bit through 64-bit plus floating-point formats.

## Matrix/AI state

Matrix execution will use an architectural accelerator context containing only state required for correct save/restore and virtualization, such as tile configuration, accumulator state, and execution configuration.

Physical AI-engine size is not exposed as a fixed physical design.

## Special state

The architecture will define exception PC, exception cause, trap value, address-translation root, interrupt state, CPU identity, machine-configuration pointer, and hypervisor state.

## Persistence

All architecturally visible state must have a representation suitable for context switching, interrupt handling, virtualization, checkpointing, and restoration.

## Design rule

Architectural registers define software-visible state. Physical register renaming, pipelines, caches, speculation, and similar mechanisms remain implementation details.
