# Coreless-64 System Fabric

## Status

Normative architecture boundary for Coreless-64.

## Purpose

The System Fabric is the common connection layer between Coreless compute, memory, storage, I/O, networking, virtualization, and 314DNest. Components communicate through defined interfaces instead of reaching directly into another subsystem's private state.

## Architectural rule

Every subsystem MUST connect through an explicit interface. A subsystem MUST NOT bypass an interface to modify another subsystem's private state.

If a new capability does not fit an existing interface, the interface is extended or a new interface is specified before implementation.

## Core interfaces

| Interface | Responsibility |
|---|---|
| Compute | CPU/vCPU execution, scheduling, execution resources |
| Memory | virtual RAM, mappings, shared-memory regions, memory telemetry |
| I/O | display, keyboard, devices, terminal, device events |
| Storage | persistent machine state and storage operations |
| Network | external and inter-system network communication |
| Fabric | messages, events, routing, service discovery |
| AI-Core | model lifecycle, inference requests, capabilities, results |
| Collaboration | AI-to-AI context, proposals, challenges, deliberation |
| Policy | validation and authorization of protected operations |

## 314DNest

**314DNest** is the codename for the architecture that houses and coordinates Coreless AI intelligence. It is not a replacement CPU and it is not a single model.

314DNest uses the System Fabric to access permitted compute, memory, storage, I/O, networking, and project state. AI models connect through the AI-Core interface and collaborate through the Collaboration interface.

Local models and external AI services use the same logical AI-Core contract. An external service such as GPT-5.6 Luna is reached through an adapter/gateway; it is not a dependency for local operation.

## Authority boundary

AI output is advisory or policy-authorized according to an explicit capability. Natural-language output is never itself an authorization token.

AI proposal -> Policy validation -> capability/resource check -> approval when required -> Coreless operation

The CPU, hypervisor, MMU, interrupt system, and other deterministic security mechanisms remain authoritative.

## Communication

Fabric messages MUST identify a source, destination/service, operation, correlation identifier, and authorization context. Components MUST reject messages that do not satisfy their interface contract.

## Failure isolation

A model failure, runtime failure, unavailable external gateway, or collaboration failure MUST NOT corrupt CPU architectural state or bypass policy. Local Coreless operation MUST remain possible without an external AI endpoint.

## Scaling

Additional CPUs, memory capacity, devices, VMs, and AI cores are resources exposed through the same interfaces. Scaling the machine MUST NOT require creating new direct connections between every pair of components.


## AI-to-resource control path

314DNest management actions reach Coreless resources only through an explicit policy-bound resource controller. The controller registers concrete operations against the Compute, Memory, Storage, I/O, and virtualization interfaces that are actually present. Each registered operation requires an opaque capability bound to that operation. A proposal without the correct capability is rejected before the underlying resource interface is called.

The protected flow is therefore:

**AI result -> structured proposal -> deterministic Policy -> capability check -> resource interface -> Coreless operation -> telemetry/audit**

Natural-language output, model identity, VM identity, storage location, or physical placement cannot substitute for a capability. Revoking a capability immediately prevents subsequent proposals from reaching the resource interface.

## Autonomous component and host boundaries

The System Fabric distinguishes two composition boundaries:

1. **Coreless Hub:** connects autonomous Coreless components while preserving component identities and execution boundaries.
2. **Coreless Host Interface:** connects the composed Coreless computer to external power and I/O transport without transferring Coreless computation or authority to the host.

The Hub may dispatch workloads by declared capability and excludes faulted components. Host transport is limited to negotiated external services such as display, input, and networking.
