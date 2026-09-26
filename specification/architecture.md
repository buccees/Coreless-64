# Coreless-64 Architecture

This document will become the source of truth for the Coreless-64 architectural contract.

## Status

Architecture design is in progress. CPU state, instruction semantics, memory, privilege, interrupts, multiprocessing, vector execution, matrix/AI execution, device interfaces, graphics, networking, and virtualization will be frozen here before implementation begins.

## Design objective

Coreless-64 is intended to define an independent portable computer architecture whose computational system travels with the device rather than depending on the host machine for CPU, GPU, system memory, operating-system execution, virtualization, or AI computation.

See [Execution Model](execution-model.md) for the separation between the architecture and its execution substrate.


## Hardware Independence Principle

Coreless-64 defines architectural behavior independently of physical implementation. CPU count, pipeline organization, cache hierarchy, execution width, vector lane count, matrix-engine count, memory technology, interconnect topology, and device implementation are not part of the instruction semantics unless explicitly exposed as architectural capability.

A reference software executor is a validation implementation, not a required execution mechanism for native Coreless hardware. Native implementations may use CPUs, FPGA fabrics, ASICs, heterogeneous accelerators, storage-integrated execution substrates, or future computational mechanisms while conforming to the same Coreless-64 architectural contract.
