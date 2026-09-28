# Coreless

**Coreless is a computer architecture in which the computational machine is carried by persistent storage.**

Coreless is not a conventional virtual machine, container, application runtime, or operating system intended to depend on a host computer for its computation.

The fundamental Coreless model is:

> **The machine is Coreless. Persistent storage carries the machine. The host provides only the external interface and startup mechanism.**

A Coreless machine is intended to contain its own:

- CPU and execution architecture
- virtual RAM
- operating system
- processes and address spaces
- storage and filesystem
- device state
- graphics and display system
- networking
- vector and matrix/AI computation
- virtualization
- applications
- persistent machine state
- boot state and checkpoints

The storage device is the persistent carrier of this machine state.

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

The architecture is independent of any particular implementation technology.

## The Coreless machine model

Coreless separates the **machine** from the mechanism used to execute the machine.

The machine consists of architectural state and persistent system state. Its execution mechanism may initially be software, then FPGA, dedicated hardware, ASIC, heterogeneous hardware, or another suitable execution substrate.

The important distinction is:

**The execution mechanism is not the machine.**

A software reference implementation may use host CPU time and host RAM to execute Coreless. Those resources are implementation mechanisms and caches; they are not the architectural CPU or RAM of the Coreless machine.

### Storage-backed virtual RAM

Coreless virtual RAM belongs to the Coreless machine.

The reference implementation therefore treats persistent storage as the authoritative backing for Coreless virtual memory. Host RAM may temporarily cache active pages, but the Coreless machine's memory state is carried by its machine image.

This is an architectural requirement, not merely a persistence feature.

### Persistent machine state

The machine image is intended to carry everything required to reconstruct the Coreless computer, including:

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

The current reference implementation is building this model incrementally. The storage format will evolve from the current reference object format into a scalable machine-image format suitable for very large virtual memory and complete machine state.

## Host relationship

The host is **not the Coreless computer**.

The intended host relationship is limited to the external mechanisms required to start and interact with a Coreless machine, such as:

- startup/power
- physical connection or transport
- monitor/display connection
- keyboard, mouse, or other input
- physical network interfaces where required

The host may provide an execution environment for the software reference implementation during development. That does not make the host part of the Coreless architecture.

The long-term goal is an independent Coreless execution substrate in which the Coreless machine does not depend on a conventional host CPU, host operating system, or host system RAM for its computation.

## Execution tracks

The project has two primary execution tracks:

1. **Reference execution** — a software implementation used to develop, test, and verify Coreless-64.
2. **Native execution** — hardware or heterogeneous execution mechanisms capable of executing the Coreless machine independently.

Potential native implementation paths include:

- FPGA
- dedicated processors
- accelerators
- ASIC
- heterogeneous compute fabrics
- storage-integrated execution

The architecture is defined independently from any one of these implementation paths.

## Scalable machine model

Coreless-64 is one architecture that can describe machines of different sizes.

A Coreless machine may expose different quantities of:

- CPU resources
- virtual RAM
- vector resources
- matrix/AI resources
- graphics resources
- persistent storage
- network resources
- guest-machine resources

Storage capacity can carry larger machine images, operating environments, applications, AI models, datasets, checkpoints, and guest machines.

Storage capacity alone does not determine computational throughput. Execution resources determine how much computation the machine can perform.

## Graphics and display

Coreless is **not headless by design**.

Graphics and display are Coreless resources. A monitor or display connection is an external interface through which the Coreless display output can be presented.

The host GPU is not intended to be the graphics processor of the Coreless machine.

## Compatibility

Coreless-native software targets Coreless-64.

Existing software may be supported through:

- binary translation
- dynamic translation
- emulation
- guest operating systems
- virtualization

Initial compatibility targets include x86-64 and ARM64.

Compatibility mechanisms are execution services around the Coreless architecture; they do not redefine Coreless-64 itself.

## Current implementation status

The project is moving from architectural specification into executable machine construction.

The reference implementation currently includes:

- Coreless-64 instruction execution
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
- complete checkpoint/restore

## Specification

- [Execution Model](specification/execution-model.md)
- [Computational Fabric](specification/computational-fabric.md)
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

> **The machine is defined independently from the mechanism that executes the machine.**

> **The computational fabric is the computer. Persistent storage carries persistent machine state. The host is the interface.**

> **If Coreless needs it to remain a computer, its state belongs in the Coreless machine image.**

Coreless is intended to become a portable computer architecture whose computational machine can travel with its persistent storage.
