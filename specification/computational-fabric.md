# Coreless-64 Computational Fabric

**Version:** 0.1  
**Status:** Architectural draft

## Objective

The Coreless computational fabric defines the independent computational system carried by a Coreless device. A conforming independent implementation is intended to execute Coreless-64 without using the host CPU as the Coreless CPU.

The host is an external interface. It may provide power and physical transport and may carry display, input, or network traffic, but those interfaces do not define Coreless computation.

## Fabric

    Coreless-64
         |
    Coreless Fabric
         |
    +----+----+----+----+----+
    |    |    |    |    |    |
   CPU Vector AI Memory GPU Storage
    |    |    |    |    |    |
    +----+----+----+----+----+
              |
          Interconnect
              |
        Network / I/O

The fabric is an architectural organization, not a requirement that every implementation use separate physical chips.

## Scalar CPU complex

Each Coreless CPU contains integer execution, control flow, load/store execution, architectural registers, privilege state, interrupt state, local translation/cache state, and synchronization support.

A machine may instantiate one or many CPUs. Software discovers the available topology.

## Vector complex

Vector execution is first-class. Coreless will use a scalable vector model rather than requiring one fixed physical vector width.

The architecture will define vector registers, element widths, vector length, masking, loads/stores, integer and floating-point operations, reductions, permutations, conversions, and cryptographic primitives where appropriate.

Scalable vector architectures in existing systems provide useful engineering reference points; current RISC-V specifications include ratified vector and vector-intrinsic standards. citeturn0search13turn0search16

## Matrix and AI complex

AI acceleration is architectural rather than an optional peripheral.

Initial target formats are INT8, INT16, INT32 accumulation, FP16, BF16, and FP32 accumulation.

The architecture will expose matrix multiply, matrix multiply-accumulate, tiled operations, vector-matrix operations, and quantized computation.

CPU, vector, and AI resources may operate concurrently.

## Coreless memory system

The memory system is independent of host system RAM.

It provides virtual address space, physical Coreless address space, protection, translation, coherent shared memory, atomic operations, synchronization, and memory-mapped device space.

The physical implementation may use one or more memory technologies.

## Coreless interconnect

The interconnect connects computational and device resources and supports memory transactions, device transactions, interrupts, synchronization, ordered communication, peer-to-peer movement, and many-core scaling.

The logical topology is a coherent fabric. The physical implementation may be a bus, crossbar, ring, mesh, network-on-chip, chiplet fabric, or another implementation.

## GPU and display

The GPU/display complex is a native Coreless resource. It provides framebuffer/display surfaces, display timing, cursor, input events, multiple displays, 2D acceleration, and future 3D/compute acceleration.

A host may transport display output without rendering Coreless graphics on the host GPU.

## Storage complex

Storage provides persistent machine state, machine-image storage, boot storage, applications, AI models, and persistent data movement.

Coreless explicitly investigates computational-storage-style execution. SNIA currently publishes computational-storage architecture and API standards, establishing that computation associated with storage is an active engineering field. citeturn0search3turn0search7

Coreless goes further: the research target is to determine whether storage-integrated execution can carry a sufficiently complete computational substrate for an independent Coreless machine.

## Network complex

The network complex provides network interfaces, packet processing, data movement, and interrupts. External networking is exposed through a host or dedicated interface without requiring the host CPU to execute Coreless software.

## Interrupts

Interrupt sources include timers, devices, network events, storage completion, display/input, inter-CPU signaling, accelerator completion, and external events.

## Multiprocessing

Coreless supports symmetric multiprocessing and large CPU counts: 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and larger implementations.

Software sees a defined Coreless topology rather than the host CPU topology.

Shared memory is architecturally coherent. Physical coherence mechanisms remain implementation-defined.

## Persistent execution state

Architectural execution state must have a defined representation suitable for suspend, resume, checkpoint, restore, migration, and duplication.

The system does not need to write storage after every instruction; implementations may maintain volatile working state and commit consistent checkpoints.

## Dynamic scaling

Machine configuration may describe different quantities of CPUs, memory, vector capacity, AI capacity, GPU resources, storage, and network interfaces.

Changing available resources must not change the Coreless-64 ISA.

Drive capacity is primarily a scaling resource for persistent state and machine-image capacity. Computational throughput comes from the execution substrate.

## Host boundary

The host is explicitly not required to provide Coreless CPU execution, Coreless RAM, Coreless GPU computation, Coreless OS execution, Coreless virtualization, or Coreless AI execution.

A development implementation may temporarily use host resources to emulate these resources. That is a development mechanism, not the target machine model.

## Native implementation requirement

A native Coreless implementation must contain an execution mechanism capable of executing Coreless-64 independently of the host CPU.

Possible implementation technologies include FPGA, ASIC, dedicated processors, heterogeneous accelerators, storage-integrated processors, or other hardware satisfying Coreless-64 semantics.

## Foundational principle

**The computational fabric is the computer. Persistent storage carries persistent machine state. The host is the interface to the computer.**
