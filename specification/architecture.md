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
