# Coreless Networking

**Version:** 0.1  
**Status:** Draft

## Native network complex

Networking is a Coreless resource rather than a function of the host OS.

The architecture provides virtual or native network interfaces, packet queues, DMA, interrupts, and link configuration.

## Protocol stack

The Coreless OS will support IPv4, IPv6, TCP, UDP, and normal application networking.

## External interface

A physical network connection may be supplied through the Coreless device or through the host interface.

The host may transport packets, but the Coreless network stack remains logically inside Coreless.

## Remote access

SSH, remote GUI protocols, file transfer, and other network applications execute within Coreless.

## Performance

The architecture permits packet-processing offload, checksum acceleration, encryption acceleration, and direct data movement without requiring the host CPU to process every packet.
