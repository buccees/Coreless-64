# Coreless

**Coreless is a project to build a portable computer architecture whose computational machine is carried with the device.**

The goal is not to build another conventional virtual machine.

The goal is to design a computer that carries its own computational architecture with it:

- Coreless CPU
- Coreless memory
- Coreless GPU/display system
- Coreless AI acceleration
- Coreless storage
- Coreless networking
- Coreless operating system
- Coreless virtualization
- Coreless applications and persistent machine state

The host machine is intended to provide the external interface required to interact with Coreless — such as power, physical connection, display, keyboard/mouse, and network connectivity — rather than supplying the CPU, GPU, system RAM, operating system execution, virtualization, or AI computation that makes Coreless itself run.

## Coreless-64

The first architecture is **Coreless-64**, a serious 64-bit general-purpose computer architecture designed from the beginning for:

- general-purpose software
- multiprocessing and scalable CPU counts
- virtual memory
- virtualization
- vector computation
- matrix and AI computation
- graphics and GUI operation
- networking
- persistent machine state
- broad software compatibility

The architecture is intended to scale without creating a different ISA for every machine size.

## The central idea

Coreless separates the **computer architecture** from the particular technology used to execute it.

The persistent Coreless machine can live on a drive while a dedicated execution substrate provides the actual instruction execution.

The development path therefore has two parallel tracks:

1. **Software execution engine** — used to develop, test, and verify Coreless-64.
2. **Native execution substrate** — the actual target for an independent Coreless computer, including investigation of FPGA, dedicated hardware, accelerators, ASICs, and storage-integrated execution.

The software implementation is not the definition of Coreless. It is the development and verification implementation of the architecture.

## Scalable machine model

Coreless is designed so that machine capacity can scale with available drive capacity and the execution substrate.

A small Coreless machine and a very large Coreless machine use the same Coreless-64 architecture while exposing different amounts of:

- CPU resources
- memory
- vector resources
- AI/matrix resources
- GPU resources
- persistent storage
- guest-machine capacity

The architecture remains the same as the machine grows.

## GUI and remote operation

Coreless is **not headless by design**.

The architecture includes a virtual display/GPU subsystem and remote interaction capabilities. SSH can be used for administration, but the graphical system is a first-class part of the computer.

## Compatibility

Coreless-native software will target Coreless-64.

To make the system useful with existing software ecosystems, compatibility layers may support other architectures such as x86-64 and ARM64 through binary translation, emulation, guest operating systems, and virtualization.

## Current status

The project is in the **architecture-design phase**.

We are deliberately defining the execution model and Coreless-64 architecture before building the emulator or native implementation. This is intended to prevent early implementation decisions from forcing a redesign of the CPU later.

## Specification

- [Execution Model](specification/execution-model.md)
- [Coreless-64 Architecture](specification/architecture.md)
- [Roadmap](ROADMAP.md)

## Project principle

> **The machine is defined independently from the mechanism that executes the machine.**

Coreless is intended to become a portable computer architecture whose computational system is carried with the device.
