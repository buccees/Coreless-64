# Coreless-64 Memory Architecture

**Version:** 0.1  
**Status:** Draft

## Goals

The memory architecture supports 64-bit computing, many-core execution, virtual memory, process isolation, virtualization, DMA, coherent shared memory, persistent state, and high-bandwidth vector/AI workloads.

## Address spaces

Coreless distinguishes:

1. virtual address space;
2. physical Coreless address space;
3. device address space;
4. persistent storage address space.

Persistent storage is not automatically treated as ordinary RAM.

## Virtual address model

Coreless-64 uses a 64-bit virtual address model with canonical addresses. The exact canonical-address rule and implemented physical-address width will be frozen with the page-table design.

## Pages

The baseline page size is 4 KiB.

Large pages are supported at 2 MiB and 1 GiB, with room for additional sizes where justified.

## Protection

Mappings provide read, write, execute, and privilege permissions plus attributes for device memory, cacheability, sharing, and accessed/dirty state.

## Translation

The architecture uses multi-level page tables and translation caches.

The translation root is privileged state.

## Memory ordering

Coreless uses an explicitly defined concurrent memory model with acquire, release, acquire-release, and stronger ordering operations.

The intent is to permit high-performance implementations without leaving concurrent behavior undefined.

## Atomics

Required atomic operations include:

- atomic load/store
- exchange
- compare-and-swap
- fetch-add
- fetch-and
- fetch-or
- fetch-xor
- memory barriers

## DMA and I/O memory

Devices may perform DMA through a controlled I/O memory-management mechanism.

Device access must be isolated from protected process memory.

## Coherence

Shared Coreless memory is architecturally coherent.

Implementations may use snooping, directory coherence, mesh coherence, or another correct mechanism.

## Persistent memory

Persistent storage is not assumed to have RAM-equivalent latency or endurance.

Coreless therefore distinguishes volatile memory from persistent storage.

Future implementations may expose persistent-memory regions with explicit persistence semantics.

## Discovery

Firmware reports:

- memory regions
- sizes
- attributes
- topology/NUMA information where applicable
- device regions
- persistent-memory regions

## Scaling

The same memory architecture must work from small machines to very large machines. Large implementations may contain multiple memory domains while preserving a unified architectural model.
