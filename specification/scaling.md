# Coreless Scaling Model

**Version:** 0.1  
**Status:** Draft

## Principle

Coreless-64 is one architecture that can instantiate machines of very different sizes.

Drive capacity is a major persistent-capacity input, while execution hardware determines computational throughput.

## Scalable resources

A Coreless machine may scale:

- CPU count
- CPU execution width
- memory capacity
- vector capacity
- AI/matrix capacity
- GPU capability
- storage capacity
- network interfaces
- guest-machine capacity

## Machine profiles

The architecture will not define separate ISAs for small, medium, and large machines.

Instead, firmware publishes a machine capability description.

## Resource discovery

Software discovers resources at boot and can query dynamic resources during operation.

## Dynamic changes

Future versions will support adding or removing resources while preserving software-visible architectural compatibility.

## Storage scaling

More drive capacity allows:

- larger OS/application environments
- more AI models
- more guest machines
- larger persistent memory images where supported
- more checkpoints
- more datasets

Storage capacity does not automatically imply more CPU throughput; native execution capacity must scale as well.

## Distributed scaling

Future Coreless systems may combine multiple Coreless devices into a single logical machine or cluster.


## Multiprocessing Architecture

### Execution contexts

Coreless-64 defines an execution context as an independently schedulable architectural CPU state. Implementations may provide 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 or more execution contexts. The ISA and software-visible machine model do not change when the implementation scales the count.

Every context has a unique architectural CPU ID. CPU IDs are used for interrupt targeting, scheduling, synchronization, topology discovery, and per-context state.

### Shared address space

All contexts may access the same architectural virtual address space when permitted by the active translation domains. Memory ordering, atomicity, and page permissions are architectural; cache hierarchy and physical memory organization are implementation-defined.

### Atomicity and coherence

Atomic instructions provide indivisible operations on their supported atomic granules. A conforming shared-memory implementation maintains coherent architectural memory values across contexts. The mechanism may be snooping, directory-based, networked, or another implementation; software depends only on the architectural coherence and ordering contract.

### Memory ordering

The Coreless memory model defines ordering through ordinary accesses, atomics, and FENCE operations. Relaxed, acquire, release, and sequentially consistent atomic orderings are architectural. Implementations may reorder internally provided the architectural model is preserved.

### Inter-processor interrupts

Contexts can send IPIs through the interrupt subsystem. IPIs support scheduler wakeups, TLB shootdowns, cross-context coordination, and machine-control events. Delivery routing and physical interrupt topology are implementation-defined.

### Startup and discovery

Machine firmware exposes the available execution contexts and their capabilities. A system may boot with a subset enabled and subsequently activate additional contexts when supported.

### Hotplug and dynamic scaling

Optional CPU hotplug permits contexts to enter and leave the scheduler under OS control. Dynamic scaling does not alter the architectural ISA. A context being offline must not receive ordinary scheduled work; machine-level control may still address it for startup or recovery.

### Topology

The architecture exposes logical CPU identity and capability discovery. Physical topology such as cores, clusters, sockets, chiplets, fabrics, or storage-adjacent execution units is implementation-defined.

### Forward scalability

The architecture does not encode a fixed maximum CPU count into instruction semantics. Resource counts are discovered through machine configuration and capability state, allowing future implementations to exceed the initial supported configurations without changing instruction meaning.

### Synchronization

Software synchronization primitives are built from atomic operations and memory ordering. Spinlocks, mutexes, barriers, semaphores, read/write locks, and scheduler primitives are software constructs unless an implementation exposes optional acceleration.

### Progress and fairness

The architecture does not require a particular scheduling or fairness policy. Implementations must preserve forward progress guarantees documented for their atomic and interrupt mechanisms.


## Dynamic Computational Resource Model

Coreless resources are discovered rather than assumed. CPU contexts, vector capacity, matrix/AI capacity, graphics resources, memory capacity, storage capacity, and device capabilities are exposed through machine configuration.

An implementation may expose different resource counts while running the same Coreless software image.

Software should query capability state and select an execution strategy rather than assuming a fixed physical topology.

### Storage versus execution capacity

Persistent storage capacity determines how much machine state, software, model data, checkpoints, datasets, and guest state can be carried. It does not by itself determine computational throughput.

Execution throughput is determined by the available computational fabric. A native implementation may co-locate execution resources with storage or attach them through a dedicated interconnect.

This separation preserves the Coreless principle that persistent machine state and computational execution are distinct architectural resources.

## Component scaling and composition

Coreless scaling also applies to autonomous computer components. Each component is a complete Coreless unit with its own execution, memory/storage, VM, AI, identity, and capabilities. Components may operate independently or connect to a Coreless Hub.

The Hub discovers specialized capabilities and routes workloads to healthy components that advertise the required capability. Adding components can increase specialized capability without changing the Coreless-64 ISA.

A host interface may expose a composed Coreless computer without becoming its computational owner.
