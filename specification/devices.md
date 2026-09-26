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
