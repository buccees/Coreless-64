# Coreless-64 Virtualization

**Version:** 0.1  
**Status:** Draft

## Objective

Coreless must be able to contain other computers.

## Hypervisor

The hypervisor runs at a privilege level above normal supervisor software.

It controls guest CPU contexts, guest memory translation, virtual interrupts, and virtual devices.

## Guest CPU

A guest CPU is a virtual instance of an architectural CPU state.

The architecture will provide efficient mechanisms for switching and protecting guest contexts.

## Memory

Guests receive isolated address spaces with controlled mappings to Coreless physical memory.

Two-stage translation will be supported where needed.

## Devices

Guest devices may be:

- emulated
- paravirtualized
- directly assigned
- mediated/shared

## Nested virtualization

Nested virtualization is a planned capability.

## Isolation

A guest must not be able to escape its assigned CPU, memory, device, storage, or network boundaries.


## Guest Virtual Memory and Nested Translation

Virtualization extends the MMU with guest translation domains.

A guest access may undergo guest-virtual to guest-physical translation followed by hypervisor-controlled guest-physical to host-physical translation.

The hypervisor controls second-stage permissions independently of guest page-table permissions. Guest translation faults and second-stage translation faults are architecturally distinguishable.

TLB invalidation may target the current host address space, a guest domain, or a virtualization-wide domain according to privilege and virtualization control state.

Nested translation is optional and capability-discoverable. Unsupported configurations are rejected through the defined capability/error mechanism.
