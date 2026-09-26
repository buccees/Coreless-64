# Coreless Execution Model

**Architecture:** Coreless-64  
**Specification:** v0.1  
**Status:** Draft

## 1. Purpose

Coreless defines a persistent, scalable computer architecture in which the complete state of a computer can be represented as a portable machine image.

The Coreless machine is intended to be an independent computer. The host is an external interface, not the computational definition of the machine.

The architecture is independent of the particular technology used to execute it.

## 2. Coreless machine

A Coreless machine consists of persistent machine state plus an execution substrate.

Persistent state includes:

- CPU configuration and state
- memory state
- firmware
- operating system
- applications
- virtual hardware state
- persistent storage
- AI models
- configuration
- user data

The execution substrate provides the mechanisms required to execute Coreless instructions and operate the machine.

## 3. Host boundary

The host is not assumed to provide the computational resources of Coreless.

The intended model is:

```
Host
  |
  +-- power
  +-- physical connection
  +-- display interface
  +-- keyboard/mouse interface
  +-- network interface
  |
  v
Coreless
  |
  +-- Coreless CPU
  +-- Coreless memory
  +-- Coreless GPU
  +-- Coreless AI engine
  +-- Coreless storage
  +-- Coreless OS
  +-- Coreless applications
```

A development implementation may temporarily use host resources to emulate these Coreless resources. That is an implementation convenience, not the target machine model.

## 4. Coreless-64

Coreless-64 is the architectural contract.

It defines:

- CPU state
- instruction semantics
- memory model
- address spaces
- privilege levels
- interrupts
- multiprocessing
- virtual memory
- vector execution
- matrix/AI execution
- device interfaces
- virtualization
- synchronization
- machine scaling

The implementation of these facilities is separate from the ISA.

## 5. Execution substrates

Coreless will support multiple implementation paths.

### 5.1 Software execution engine

The first executable implementation will be a software engine used to develop and verify Coreless-64.

It will:

1. load a Coreless machine image;
2. instantiate the defined Coreless resources;
3. execute Coreless-64 instructions;
4. maintain architectural state;
5. provide virtual devices;
6. provide persistent storage;
7. provide display and input;
8. provide networking;
9. support multiple Coreless CPUs.

The software engine is a reference implementation, not the intended computational dependency of the finished Coreless system.

### 5.2 Native execution substrate

The target architecture must be implementable without borrowing the host machine's general-purpose CPU as the Coreless CPU.

Potential implementations include:

- FPGA
- dedicated accelerator
- ASIC
- custom processor
- heterogeneous execution hardware
- storage-integrated execution hardware

All implementations must preserve Coreless-64 architectural behavior.

### 5.3 Storage-integrated execution

Coreless will explicitly investigate moving computation into or close to persistent storage.

This includes research into:

- programmable storage controllers
- computational storage
- storage-side accelerators
- persistent-memory architectures
- distributed execution across storage devices
- future storage-integrated processors

The goal is to determine how much of the Coreless computational system can be physically carried with persistent storage.

## 6. Persistent machine image

A Coreless machine image represents the persistent computer.

It may contain:

```
Coreless Machine
|
+-- machine configuration
+-- CPU configuration/state
+-- memory state
+-- firmware
+-- operating system
+-- virtual devices
+-- device state
+-- persistent storage
+-- applications
+-- AI models
+-- user data
+-- metadata
```

The image should be portable between compatible Coreless implementations.

## 7. CPU execution

Coreless-64 instruction execution follows the architectural sequence:

```
Fetch
  -> Decode
  -> Execute
  -> Memory / Device Access
  -> Commit Architectural State
  -> Next Instruction
```

The internal pipeline is implementation-defined unless explicitly exposed by the architecture.

## 8. Scalable resources

Coreless-64 is designed to support different machine sizes without changing the ISA.

Possible configurations include:

- 1 CPU
- 4 CPUs
- 16 CPUs
- 64 CPUs
- 256 CPUs
- 1024 CPUs
- and larger configurations

Other resources can scale independently:

- memory
- vector capacity
- matrix/AI capacity
- GPU capacity
- storage
- guest-machine capacity

Drive capacity is a key scaling input for persistent machine state and machine-image capacity. It does not, by itself, create computational throughput; the execution substrate must provide that capability.

## 9. Memory

Coreless distinguishes:

1. architectural memory;
2. persistent storage;
3. implementation-specific physical memory.

A software reference implementation may use host memory to represent Coreless memory.

A native implementation may use dedicated memory or another suitable technology.

The Coreless operating environment sees the Coreless memory model rather than the host's physical memory organization.

## 10. Devices

Initial architectural devices include:

- CPU
- memory controller
- interrupt controller
- timer
- storage controller
- network controller
- display/GPU controller
- keyboard
- pointer
- audio
- random-number source

Device interfaces will be specified separately.

## 11. Graphics and display

Coreless is not headless by design.

The architecture will support:

- framebuffer
- display resolution
- pixel formats
- cursor
- keyboard input
- pointer input
- display events
- multiple displays
- accelerated graphics

Remote display is an interface to the Coreless GPU/display system, not a substitute for it.

## 12. Networking

Coreless includes a virtual network subsystem supporting:

- network interfaces
- packet transmission and reception
- IPv4/IPv6
- TCP/UDP
- remote administration
- external network connectivity where available

SSH is an application that can run on the Coreless network stack; it is not the graphical or computational architecture.

## 13. Virtualization

Coreless-64 will include architectural support for hosting additional machines.

A Coreless system may eventually contain:

```
Coreless
|
+-- Coreless OS
+-- Guest Machine A
+-- Guest Machine B
+-- Guest Machine C
```

Virtualization will cover CPU, memory, interrupts, devices, storage, and networking.

Nested virtualization is a future capability.

## 14. AI and accelerated execution

AI is a first-class architectural requirement.

Coreless-64 will provide scalable vector and matrix/AI execution.

Target numerical formats include:

- FP16
- BF16
- FP32
- FP64
- INT8
- INT16
- INT32
- INT64

The exact instruction encoding and accelerator organization will be specified separately.

## 15. Compatibility

Coreless-native programs target Coreless-64.

Existing software may be supported through:

- binary translation
- dynamic translation
- emulation
- guest operating systems
- virtualization

Initial compatibility targets include x86-64 and ARM64.

Compatibility is a software/platform layer and does not redefine Coreless-64.

## 16. Portability and persistence

A Coreless machine image should be able to be:

- copied
- backed up
- restored
- duplicated
- migrated
- expanded
- reduced
- executed by compatible implementations

The machine image should not require a specific host CPU architecture.

## 17. Architectural principle

> **The machine is defined independently from the mechanism that executes the machine.**

The persistent Coreless machine is the computer being designed. Execution hardware is the mechanism that gives that machine computational activity.

The long-term target is an independent portable computer whose computational architecture travels with the device.

## 18. Open engineering questions

The project must investigate:

1. What minimum execution substrate is required for a fully independent Coreless machine?
2. How much computation can be performed by storage-integrated hardware?
3. How should Coreless memory be physically implemented?
4. How should persistent machine state and active execution state interact?
5. How should CPU, GPU, and AI resources scale?
6. Can multiple Coreless storage devices cooperate as one machine?
7. How should resources be added or removed while preserving the machine architecture?
8. What interconnect should join Coreless CPU, memory, GPU, AI, storage, and I/O?
9. What native implementation provides the required performance and efficiency?
10. How can the host be reduced to an interface while Coreless remains computationally independent?

These questions are engineering problems within the Coreless architecture, not reasons to redefine the project's objective.

## 19. Versioning

Breaking architectural changes require a new Coreless architecture revision.

Implementation improvements must not require changes to existing Coreless software unless explicitly documented.
