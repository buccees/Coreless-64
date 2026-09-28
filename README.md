# Coreless

**Coreless is a project to build a portable computer architecture whose computational machine is carried with the device.**

The goal is not to build another conventional virtual machine.

The goal is to design a computer that carries its own computational architecture with it:

- Coreless CPU
- Coreless virtual RAM backed by persistent storage
- Coreless GPU/display system
- Coreless AI acceleration
- Coreless storage
- Coreless networking
- Coreless operating system
- Coreless virtualization
- Coreless applications and persistent machine state

The host is intended to provide only the external interface required to interact with Coreless — such as startup/power, physical connection, display, keyboard/mouse, and network connectivity. The host is not intended to own the CPU, GPU, system RAM, operating-system execution, virtualization, or AI computation that makes Coreless itself a computer.

## Coreless-64

The first architecture is **Coreless-64**, a 64-bit general-purpose architecture designed from the beginning for general software, multiprocessing, virtual memory, virtualization, scalable vector computation, matrix/AI computation, graphics, networking, persistent state, and broad software compatibility.

The architecture scales without creating a different ISA for every machine size.

## The central idea

**The Coreless computational fabric is the computer. Persistent storage carries the machine. The host is the interface.**

Coreless virtual RAM is part of the machine carried by storage. Host RAM may be used by a software reference implementation as a cache or execution mechanism, but it is not the architectural owner of Coreless memory.

The reference machine now uses one shared Coreless RAM space across CPUs, persists touched RAM pages to the machine image, and persists architectural CPU state so a machine image can be reopened with its prior machine state.

The long-term storage format will evolve beyond the current reference object format toward scalable machine images capable of carrying very large virtual memory and complete machine state efficiently.

## Execution tracks

The project has two execution tracks:

1. **Reference software execution engine** — used to develop, test, and verify Coreless-64.
2. **Native execution substrate** — the actual target for an independent Coreless computer.

The native path explicitly investigates FPGA, dedicated hardware, accelerators, ASICs, heterogeneous fabrics, and storage-integrated execution.

The reference software implementation is not the final computational dependency of Coreless.

## Scalable machine model

Coreless uses one architecture for many machine sizes. Available drive capacity can support larger persistent machine images, operating environments, AI models, datasets, checkpoints, guest machines, and other state. Native execution capacity determines computational throughput.

The same Coreless-64 architecture can expose different quantities of:

- CPU resources
- virtual RAM
- vector resources
- AI/matrix resources
- GPU resources
- persistent storage
- network resources
- guest-machine capacity

## GUI

Coreless is **not headless by design**.

The GPU/display subsystem is a first-class Coreless resource. A host may transport the resulting display and input, but the host GPU is not required to render the Coreless computer.

## Compatibility

Coreless-native software targets Coreless-64.

Existing software may be supported through binary translation, dynamic translation, emulation, guest operating systems, and virtualization. Initial compatibility targets include x86-64 and ARM64.

## Current status

The project is moving from architecture specification into executable machine construction.

The reference implementation now has persistent storage-backed virtual RAM, shared RAM across CPUs, and persisted architectural CPU state. The next implementation work is to carry the remaining machine subsystems — operating environment, processes, device state, boot state, and application state — into the same persistent machine model.

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

## Project principle

> **The machine is defined independently from the mechanism that executes the machine.**

Coreless is intended to become a portable computer architecture whose computational system is carried with the device.
