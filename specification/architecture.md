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


## External host and plug-and-play boundary

The Coreless computer has a deliberately narrow external boundary. A host may provide power/startup and transport for display, keyboard/pointer/input, networking, and other explicitly negotiated I/O.

The host is not the Coreless computational owner. Host CPU execution, host system RAM, host operating-system execution, host virtualization, and host AI computation are not architectural dependencies of Coreless.

Coreless components may connect through a Coreless Hub and form a unified computer while retaining autonomous execution, VM, AI, identity, and specialization boundaries.

The normative plug-and-play host contract is defined in [Host Interface](host_interface.md).

## Security Architecture

Security is part of the architectural machine model.

### Trust domains

The baseline trust hierarchy is:

Machine firmware → hypervisor → supervisor/OS → user processes.

Each domain is isolated by privilege, translation, device protection, and architectural state ownership.

### Secure boot

Machine firmware may verify the next boot stage before transferring control. Verification mechanisms are implementation-defined, but the architectural boot state must expose whether the machine entered a verified or recovery state when that information is available.

### Memory protection

MMU permissions, privilege checks, device domains, and DMA isolation prevent unauthorized access between protection domains.

### Capability discovery

Optional security, cryptographic, accelerator, memory, and device features are discovered rather than assumed. Software must not rely on unavailable capabilities.

### Cryptographic acceleration

The CRYPTO instruction family provides an architectural extension point for cryptographic primitives. Implementations may accelerate these operations or execute them through another conforming mechanism.

### Fault containment

Machine faults must not silently create architectural access to another protection domain. Fatal faults enter machine-level handling or defined recovery behavior.


## Reset State

On architectural reset:

- execution begins in Machine privilege;
- interrupts are disabled;
- the translation root is inactive unless machine firmware explicitly establishes one;
- PC is loaded from the implementation-defined reset vector;
- SP is undefined until machine firmware initializes it;
- general-purpose registers are architecturally undefined unless explicitly specified by the boot environment;
- vector and matrix state are disabled/initially inactive;
- virtualization is disabled;
- device DMA is disabled until its protection domain is configured;
- security/boot status reports the machine's reset and verification state.

Machine firmware is responsible for establishing memory, interrupt, translation, device, and execution-context configuration before transferring control to Supervisor or another lower privilege domain.

A reset vector and machine configuration pointer are implementation-defined machine inputs, but their existence and handoff semantics are architectural.


## AI and tensor execution boundary

Coreless-64 exposes vector and matrix execution as architectural resources. The native AI/TensorRuntime layer builds higher-level tensor operations from those resources while preserving a deterministic boundary between model code and Coreless execution.

The current reference implementation includes TensorRuntime primitives for vector/matrix arithmetic, RMS normalization, scalar broadcast, transpose, rotary trigonometric operations, masking, scalar scaling, and deterministic argmax. Qwen3 uses these paths for progressively more of its attention and normalization execution.

These TensorRuntime operations are implementation/runtime contracts, not replacements for the ISA. Where an operation maps to architectural vector or matrix execution, the implementation must preserve the architectural semantics, capability checks, and deterministic error behavior of those underlying resources.

The remaining native-runtime work is to move Qwen3 KV-cache storage, head reshaping/repetition, and attention data movement into TensorRuntime so that model execution does not fall back to host-side Python data structures for those boundaries.

## Capability Discovery

Architectural capabilities are discovered rather than inferred from implementation identity. CAP_BASE points to a read-only capability table containing a versioned header followed by fixed-size device/resource records. The table describes execution contexts, vector width, supported element types, matrix tile shapes, physical address width, virtualization support, graphics/network/storage capabilities, and optional extensions.

Software must query capabilities before using optional architectural resources. Unsupported operations or resource requests produce a capability/resource fault rather than silently changing semantics. The capability table is part of the machine boot contract and remains available after Supervisor handoff.