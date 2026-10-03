# Coreless Execution Model

**Architecture:** Coreless-64  
**Specification:** v0.1  
**Status:** Draft

## 1. Purpose

Coreless defines a persistent, scalable digital computer architecture in which the complete state of a computer can be represented by a portable machine image and executed by a Coreless digital execution engine.

Coreless is intended to be an independent computer. The external environment provides power and I/O; it is not the computational definition of the Coreless machine.

## 2. Machine and execution engine

The Coreless **machine** is the computer being defined.

It includes:

- CPU architectural state
- instruction semantics
- virtual RAM
- address spaces
- processes
- operating-system state
- devices
- graphics
- networking
- filesystem
- applications
- persistent state

The Coreless **digital execution engine** is the mechanism that executes that machine.

The distinction is logical:

> **The machine defines what the computer is and what state it has. The digital execution engine makes that defined machine execute.**

Both belong to Coreless.

The execution engine is not an external host computer that Coreless requires for its architectural CPU, RAM, OS, or computation.

## 3. Digital execution loop

The Coreless execution engine follows the architectural execution model:

    Fetch
      ↓
    Decode
      ↓
    Execute
      ↓
    Memory / Device Access
      ↓
    Commit Architectural State
      ↓
    Next Instruction

The current repository implements this model in software so that the complete digital machine can be executed and tested now.

## 4. Current engine

The current Coreless digital execution engine is part of this repository.

reference/core.py implements Coreless-64 CPU instruction execution.

reference/machine_runtime.py integrates the CPU execution engine with:

- shared Coreless virtual RAM
- persistent machine storage
- interrupts
- devices
- graphics/display
- networking
- filesystem
- virtualization
- persistent machine state

This is the executable Coreless machine model currently under development.

## 5. Persistent machine image

A Coreless machine image carries persistent machine state.

It may contain:

    Coreless Machine Image
    |
    +-- machine configuration
    +-- CPU state
    +-- virtual RAM
    +-- address-space state
    +-- process state
    +-- operating-system state
    +-- device state
    +-- filesystem state
    +-- graphics state
    +-- networking state
    +-- applications
    +-- AI models
    +-- checkpoints

The current storage implementation is intentionally simple. It will evolve toward a scalable machine-image format.

## 6. External boundary

The intended external boundary is small:

    External environment
      |
      +-- power
      +-- physical connection
      +-- monitor/display
      +-- keyboard/mouse/input
      +-- network connection
      |
      v
    Coreless digital execution engine
      |
      v
    Coreless machine

The external environment is an interface to the machine.

A development platform may host the software implementation of the execution engine, but those host resources are not the architectural resources of Coreless.

## 7. Virtual RAM

Coreless virtual RAM belongs to the machine.

The current engine uses persistent storage as authoritative backing for virtual RAM. Active pages can be cached by the implementation, but the persistent machine image owns the machine's durable memory state.

## 8. CPU execution

Each Coreless CPU executes Coreless-64 instructions according to the architectural specification.

The engine is responsible for:

- instruction fetch
- instruction decoding
- instruction execution
- register updates
- memory translation
- memory access
- traps and exceptions
- interrupts
- privilege transitions
- architectural retirement

Implementation details such as internal scheduling and caching do not change the architectural behavior.

## 9. Multiprocessing

A Coreless machine may contain one or many Coreless CPUs.

The execution engine schedules those CPUs while preserving the Coreless shared-memory and synchronization model.

The architectural CPU count is a property of the Coreless machine, not the host platform used to run the software implementation.

## 10. Devices

The execution engine connects the machine to Coreless device models.

Initial device classes include:

- timer
- interrupt controller
- storage
- network
- display
- input
- other architectural devices as they are implemented

Device state belongs to the Coreless machine image when it is required for machine continuity.

## 11. Graphics and networking

Graphics and networking are Coreless machine resources.

External displays and network links are interfaces through which those resources communicate with the outside world.

The host does not become the Coreless GPU or network stack merely because the current software implementation uses host interfaces.

## 12. Compatibility

Compatibility layers may execute on top of the Coreless execution engine.

Possible mechanisms include:

- binary translation
- dynamic translation
- emulation
- guest operating systems
- virtualization

These mechanisms provide software compatibility without redefining the Coreless-64 machine.

## 13. Implementation independence

The Coreless machine specification is independent of any particular implementation of its execution engine.

The current engine is software.

Future implementations may use other digital execution technologies.

Those alternatives must preserve the defined Coreless-64 architectural behavior.

The architecture does not require a particular physical implementation technology.

## 14. Coreless objective

The finished system should behave as a self-contained digital computer:

    Persistent machine state
            +
    Coreless digital execution
            =
    Coreless computer

External equipment supplies power and I/O rather than supplying the computer's architectural identity or computation.

## 6A. Plug-and-play host interface

The external environment is presented through a Coreless host interface.

The intended lifecycle is: **connect → discover → verify identity → advertise capabilities → negotiate → attach → boot/resume → operate → detach**.

The host supplies external I/O transport. It does not supply Coreless architectural CPU, RAM, OS execution, VM execution, AI computation, or policy authority.

The host interface connects to the Coreless Hub; autonomous components retain their identities and can continue independently after detachment.

See [Host Interface](host_interface.md).
