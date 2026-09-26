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


## Virtual Memory and MMU Architecture

Coreless-64 uses 64-bit virtual addresses. Physical-address width and supported virtual-address modes are capability-discoverable.

The baseline page size is 4 KiB. Larger pages may be supported through higher-level leaf mappings. The architecture supports multi-level page tables, distinct address spaces, read/write/execute permissions, user/supervisor access control, accessed and dirty state, global/shared mappings, memory attributes, and device mappings.

Each execution context has a privileged translation root identifying the active address space. Changing the root is ordered with subsequent translation according to MMU synchronization rules.

A mapping may specify read, write, execute, user accessibility, global status, accessed/dirty state, cacheability, device ordering, and implementation-defined attributes. Instruction fetch requires execute permission. User execution cannot access supervisor-only mappings.

Translation faults include page-not-present, permission, execute-never, privilege, malformed-page-table, invalid-attribute, and physical-address-range faults. Faults are precise and identify the failing virtual address.

TLBs are microarchitectural. Their size, organization, replacement policy, and hierarchy are implementation-defined. Software observes architectural translation behavior and explicit invalidation operations. TLBFLUSH invalidates applicable translations; TLBFLUSHVA invalidates translations associated with a supplied virtual address.

Operating systems may assign distinct translation roots to processes and execution environments. User mappings must not expose supervisor mappings unless explicitly permitted. The MMU distinguishes normal cacheable, normal non-cacheable, and device memory.

Software must make page-table writes visible before activating or invalidating affected translations. The required sequence uses FENCE and TLB invalidation operations.

Translation state may be local to each execution context. Mapping changes visible to multiple contexts require invalidation on each affected context, normally using IPIs plus local invalidation. Implementations may provide coherent shared TLBs.

CPU virtual-memory translation is distinct from device/DMA translation. An optional I/O MMU may provide capability-discoverable device translation domains and isolation.

A faulting memory instruction does not retire its destination or store side effect. Exception state permits the handler to resolve the fault and restart the instruction. Vector and matrix memory operations follow their defined precise-fault and restart rules.

The architecture provides canonical-address checking so implementations with less than 64 physical address bits can reject invalid virtual addresses deterministically. Supported canonical modes are capability-discoverable.

## Baseline Page-Table Entry Format

Coreless-64 uses a 64-bit page-table entry for the baseline 4 KiB mapping format.

| Bits | Field |
|---|---|
| 0 | valid |
| 1 | read |
| 2 | write |
| 3 | execute |
| 4 | user |
| 5 | global |
| 6 | accessed |
| 7 | dirty |
| 9:8 | memory type |
| 10 | software/COW |
| 11 | reserved |
| 47:12 | physical page number |
| 59:48 | architecture-defined attributes |
| 63:60 | extension/capability attributes |

Memory type values are 0 normal cacheable, 1 normal non-cacheable, 2 device, and 3 reserved.

A leaf entry is valid only when its permission and attribute combinations are legal. A writable mapping without read permission is allowed only when the implementation advertises write-only memory support; otherwise it is a malformed mapping.

Physical-address bits above the implemented physical width must be zero. Reserved fields must be zero. A malformed entry raises the malformed-translation fault.

Higher-level entries may be non-leaf pointers or leaf mappings for larger pages. The page-table walker validates alignment and reserved bits before using a mapping.
