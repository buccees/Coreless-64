# Coreless-64 Digital Execution Engine

**Version:** 0.1  
**Status:** Architectural draft

## Objective

The Coreless digital execution engine is the computational mechanism that makes the Coreless-64 machine execute.

It is part of the Coreless design.

It is not a physical fabric, a separate host computer, or an external CPU that Coreless depends upon.

The current implementation is software. The architecture is defined independently from the implementation technology.

## Machine relationship

    CORELESS
    +---------------------------------------+
    | Persistent Coreless Machine           |
    |                                       |
    | CPU state / RAM / OS / processes      |
    | devices / graphics / network / apps   |
    |                                       |
    |              ^                        |
    |              | executes               |
    |              |                        |
    |     Coreless Digital Execution        |
    |              Engine                   |
    +---------------------------------------+
                    |
            External interfaces
           power / display / input /
                 networking

The machine defines the state and behavior of the computer.

The execution engine performs the state transitions that make that computer run.

## Current implementation

The first Coreless digital execution engine is already in this repository.

- reference/core.py — Coreless-64 CPU execution
- reference/machine_runtime.py — machine-level integration
- reference/memory.py — Coreless virtual RAM
- reference/storage.py — persistent machine image
- reference/device_io.py — device interfaces
- reference/filesystem.py — persistent filesystem
- reference/virtualization.py — virtualization model

The engine currently executes scalar Coreless-64 instructions and integrates the architectural CPU with persistent memory, interrupts, devices, and machine state.

Vector and matrix/AI execution remain implementation work in the reference engine.

## Execution cycle

The basic digital execution cycle is:

    Fetch
      -> Decode
      -> Execute
      -> Memory / Device Access
      -> Commit
      -> Advance

Architectural state is updated according to Coreless-64 semantics.

## CPU execution

The engine maintains Coreless CPU state including:

- 32 general-purpose registers
- program counter
- stack pointer
- privilege level
- control/status registers
- interrupt state
- exception/trap state
- TLB state
- atomic reservation state
- vector state
- matrix state
- cycle and retirement counters

The engine does not treat the host CPU register file as Coreless architectural state.

## Memory execution

The engine accesses Coreless virtual RAM through the Coreless memory model.

The current implementation provides:

- 4 KiB virtual RAM pages
- persistent page backing
- shared machine RAM across CPUs
- virtual address translation
- permissions
- TLB state
- page-fault behavior

Host memory may be used internally while the software engine runs, but Coreless memory remains a Coreless machine resource.

## Device execution

The engine connects instruction execution to Coreless device state.

Devices include or are being developed for:

- interrupts
- timers
- storage
- networking
- graphics/display
- input
- virtualization

The goal is for device state needed to preserve the computer to become part of the persistent machine image.

## Multiprocessing

The engine can instantiate multiple Coreless CPUs.

All CPUs address the shared Coreless machine memory model.

CPU identity and CPU count are Coreless architectural state rather than host topology.

The reference implementation will continue to improve memory coherence and scheduling semantics as the multiprocessing model is completed.

## Persistent execution

A running Coreless machine has volatile working state and persistent machine state.

The engine can:

- flush machine memory
- persist CPU state
- checkpoint the machine
- restore machine state
- resume from a machine image

The machine image is the durable representation of the Coreless computer.

## External I/O

The engine exposes Coreless resources to external interfaces.

A monitor presents Coreless display output.

Keyboard/mouse/input devices provide Coreless input.

A network interface provides external connectivity.

Power starts and sustains the system.

None of these interfaces becomes the Coreless CPU, RAM, OS, or execution engine.

## Future implementations

The software engine is the current executable implementation of Coreless.

The same architectural machine may later be implemented using other digital execution technologies.

Such implementations are implementation choices, not architectural dependencies.

The project does not require a particular physical fabric for Coreless to be a valid computer architecture.

## Foundational principle

> **Coreless is the computer. The Coreless digital execution engine runs the computer. Persistent storage carries its persistent machine state. External equipment provides power and I/O.**
