# Coreless

**Coreless is a computer architecture in which the complete digital computer can be carried by persistent storage and executed by a digital Coreless execution engine.**

Coreless is not intended to be a conventional virtual machine that depends on a host computer to provide its CPU, RAM, operating system, or graphics.

The fundamental model is:

> **Coreless is the computer. Persistent storage carries the machine state. The Coreless digital execution engine runs the machine. External equipment provides power and I/O.**

A Coreless machine includes:

- Coreless CPU and instruction execution
- virtual RAM
- operating system
- processes and address spaces
- filesystem and persistent storage
- device state
- graphics and display
- networking
- vector and matrix/AI computation
- virtualization
- applications
- persistent machine state
- boot state and checkpoints

The machine and the mechanism that executes it are logically distinct, but both are part of the Coreless design. The execution engine is not an external computer that Coreless depends on.

## Coreless-64

The first Coreless architecture is **Coreless-64**, a 64-bit general-purpose computer architecture designed for:

- general-purpose computation
- multiprocessing
- virtual memory and memory protection
- privilege separation
- interrupts and exceptions
- vector computation
- matrix and AI computation
- graphics and display
- networking
- virtualization
- persistent machine state
- scalable machine configurations
- compatibility with existing software through translation and virtualization

The architecture defines the digital machine. The execution engine implements those architectural rules.

## The Coreless machine and execution engine

Coreless makes an important distinction between the **machine** and its **execution engine**.

The **machine** is the computer being defined:

- architectural registers and CPU state
- memory and address spaces
- instruction semantics
- processes
- OS state
- devices
- filesystem
- graphics
- networking
- applications
- persistent state

The **digital execution engine** is the mechanism that makes that defined machine execute:

**fetch → decode → execute → memory/device access → commit state → next instruction**

The current software execution engine is already part of this repository. reference/core.py contains the Coreless-64 CPU execution implementation, and reference/machine_runtime.py integrates those CPUs, memory, devices, and persistent machine state into a Coreless machine.

This software engine is not a host dependency in the Coreless architecture. It is the current digital implementation of the Coreless execution mechanism, used to make the complete machine executable, testable, and persistent.

Later implementations may use different digital execution technologies while preserving the same Coreless-64 machine behavior. No particular hardware technology is required by the architecture.

## Persistent machine state

Persistent storage is the authoritative carrier of the Coreless machine state.

The machine image is intended to carry everything required to reconstruct the computer, including:

- CPU architectural state
- virtual RAM
- page and address-space state
- process state
- operating-system state
- device state
- filesystem state
- application state
- networking state
- graphics state
- virtualization state
- boot state
- checkpoints and other persistent state

The current reference storage format is an incremental implementation. It will evolve into a scalable machine-image format suitable for very large virtual memory and complete machine state.

### Storage-backed virtual RAM

Coreless virtual RAM belongs to the Coreless machine.

The current engine uses persistent storage as the authoritative backing for Coreless virtual memory. Active pages may be cached by the implementation, but the architectural memory state belongs to the Coreless machine image.

This is an architectural requirement, not merely a persistence feature.

## External boundary

The external environment is an interface to Coreless, not the computer that executes it.

The intended external requirements are limited to things such as:

- USB or other power
- physical connection or transport
- monitor/display
- keyboard, mouse, or other input
- network connection

The Coreless digital execution engine provides the computation. The external equipment provides the means to power and interact with the computer.

During development, the software engine necessarily executes on some development platform. That does not make the development platform part of the Coreless machine.

## Digital execution

The current repository provides a software implementation of the Coreless digital execution mechanism.

At the machine level:

    Persistent Coreless Machine Image
                |
                v
        Coreless Digital Engine
                |
                v
        Coreless machine state
                |
                +----> persistent machine image

The engine executes Coreless instructions and updates the machine state. The machine state can then be persisted, restored, checkpointed, or resumed.

The execution engine therefore belongs **inside the Coreless project and machine model**, rather than being treated as an unrelated host-side emulator.

## Graphics and display

Coreless is not headless by design.

Graphics and display are Coreless resources. A monitor is an external display interface for Coreless output.

The host GPU is not the architectural graphics processor of Coreless.

## Networking

Networking is a Coreless machine resource. External network connectivity is an interface available to the Coreless network subsystem.

The host or attached network interface transports packets; Coreless networking logic and state belong to the Coreless machine.

## Compatibility

Coreless-native software targets Coreless-64.

Existing software may be supported through:

- binary translation
- dynamic translation
- emulation
- guest operating systems
- virtualization

Initial compatibility targets include x86-64 and ARM64.

Compatibility mechanisms do not redefine Coreless-64.

## Scalable machine model

Coreless-64 describes machines of different sizes without changing the architecture.

A machine may expose different quantities of:

- CPU resources
- virtual RAM
- vector resources
- matrix/AI resources
- graphics resources
- persistent storage
- network resources
- guest-machine resources

Storage capacity can carry larger machine images, operating environments, applications, AI models, datasets, checkpoints, and guest machines.

Storage capacity alone does not create computational throughput. The digital execution engine determines what computational resources the machine provides.

## Current implementation status

The project is moving from architectural specification into an executable, persistent digital computer. The reference machine now persists and restores complete machine-image checkpoints, including CPU, RAM, OS, process, device, graphics, filesystem, and application/session state.

The repository currently includes:

- Coreless-64 instruction execution
- digital CPU execution engine
- persistent machine storage
- storage-backed virtual RAM
- shared Coreless RAM across CPUs
- persisted architectural CPU state
- multiprocessing foundations
- virtual memory/MMU foundations
- interrupt and device foundations
- graphics/display foundations
- networking foundations
- virtualization foundations

The next major implementation work is to make the remaining machine subsystems persistent parts of the same Coreless machine image, including:

- process and address-space state
- operating-system state
- device state
- boot state
- application state
- complete machine-image checkpoint/restore

## Specification

- [Execution Model](specification/execution-model.md)
- [Digital Execution Engine](specification/computational-fabric.md)
- [Coreless-64 Architecture](specification/architecture.md)
- [Registers](specification/registers.md)
- [ISA](specification/isa.md)
- [Memory](specification/memory.md)
- [Privilege](specification/privilege.md)
- [Interrupts](specification/interrupts.md)
- [ABI](specification/abi.md)
- [Devices](specification/devices.md)
- [Graphics](specification/graphics.md)
- [Networking](specification/networking.md)
- [Virtualization](specification/virtualization.md)
- [Roadmap](ROADMAP.md)

## Project principles

> **Coreless is the computer. The Coreless digital execution engine runs the computer.**

> **Persistent storage carries persistent machine state.**

> **The external environment is the interface, not the computational owner of Coreless.**

> **If Coreless needs it to remain a computer, its state belongs in the Coreless machine image.**

Coreless is intended to become a portable digital computer architecture whose machine can travel with its persistent storage.
