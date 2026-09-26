# Coreless Device Architecture

**Version:** 0.1  
**Status:** Draft

## Device classes

Coreless defines architectural interfaces for:

- storage
- network
- display/GPU
- keyboard
- pointer
- audio
- timer
- interrupt controller
- random source
- accelerator engines

## Device discovery

Firmware provides a machine description identifying device types, resources, interrupts, capabilities, and topology.

## MMIO

Devices may expose control registers through memory-mapped I/O.

## DMA

High-bandwidth devices may use DMA through an I/O memory-management mechanism.

## Queues

Performance-oriented devices will use shared-memory command/completion queues where practical.

This applies especially to storage, network, GPU, and AI devices.

## Isolation

Device access is privilege-controlled and can be virtualized for guests.

## Device and Interconnect Independence

Coreless devices are architectural resources presented through a capability-discoverable device model. Device implementation, bus topology, link technology, physical controller placement, and transport are implementation-defined.

The computational fabric may connect scalar execution, vector engines, matrix/AI engines, memory, storage, graphics, networking, and accelerators through any implementation interconnect that preserves the architectural ordering, interrupt, DMA, and visibility rules.

Software addresses architectural device resources rather than assuming PCIe, USB, SATA, NVMe, or another host-specific transport. Compatibility layers may expose such external protocols where required.

### Device discovery

Firmware exposes device identity, capability, resource ranges, interrupt routes, DMA capabilities, and optional acceleration features through an architectural discovery mechanism.

### DMA

Devices may perform DMA only within permitted translation and protection domains. DMA visibility follows the architectural device-memory and fence rules.


## Device Architecture Baseline

The architectural device model consists of discoverable resources, memory-mapped or capability-defined control interfaces, event/interrupt delivery, DMA domains, and synchronization rules.

A device implementation is conforming when it provides the specified architectural behavior regardless of whether its physical realization is a bus controller, accelerator, FPGA region, chiplet, ASIC block, or storage-adjacent engine.

### Resource discovery

The discovery interface reports device type, version, capabilities, resource regions, interrupt capabilities, DMA domain, and optional acceleration features.

### Device isolation

Device resources belong to explicit protection domains. Access from lower privilege requires an architectural permission path.

### Command completion

Asynchronous device commands complete through interrupts or event mechanisms. Completion visibility follows the device-memory and DMA ordering rules.
