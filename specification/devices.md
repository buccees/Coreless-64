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


## Device Discovery Record

Coreless devices are discovered through a capability table rooted at CAP_BASE. Each device record is 64 bytes and begins on a 64-byte boundary.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | device type |
| 0x04 | 4 | device version |
| 0x08 | 8 | capability bits |
| 0x10 | 8 | resource base |
| 0x18 | 8 | resource length |
| 0x20 | 4 | interrupt base/identifier |
| 0x24 | 4 | interrupt count |
| 0x28 | 8 | DMA domain |
| 0x30 | 8 | command/completion interface |
| 0x38 | 8 | implementation/extension pointer |

A zero device type terminates the table. Unknown nonzero device types are skipped using the fixed record size. Resource ranges must be aligned and non-overlapping within their declared address domain. Device capability bits are self-describing; unsupported optional features must not be assumed.
## Host interface device boundary

Host-provided transport is an external interface to Coreless devices, not the definition of those devices.

A host connection may transport display output, input events, network packets, startup/power control, and other explicitly negotiated device events. Coreless owns architectural device state, permissions, queues, interrupts, DMA domains, and resource semantics.

The host transport MUST NOT silently substitute host computation for Coreless execution. See [Host Interface](host_interface.md).
