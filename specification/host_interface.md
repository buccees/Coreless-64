# Coreless Plug-and-Play Host Interface

**Architecture:** Coreless-64  
**Status:** Software contract and reference host I/O integration implemented; physical transport adapters remain

## Purpose

The Coreless host interface defines the narrow boundary between a Coreless computer and external equipment.

The host is an interface provider, not the Coreless computer. Coreless carries its own architectural state, execution, memory/storage, operating environment, AI, component identity, and system composition.

The target is a plug-and-play experience in which a host can discover a Coreless computer, verify its identity, negotiate supported interfaces, attach it, and provide only the external services required for operation.

## Host responsibilities

The host may provide:

- power/startup
- display output transport
- keyboard, pointer, and other input transport
- network connectivity
- other explicitly negotiated I/O transport

The host does **not** become:

- the Coreless CPU
- Coreless system RAM
- the Coreless operating system
- the Coreless VM/hypervisor
- the Coreless AI runtime
- the Coreless architectural authority

## Connection boundary

```text
                    EXTERNAL HOST
        +----------------------------------+
        | Power / startup                  |
        | Display transport                |
        | Keyboard / pointer / input      |
        | Network / external I/O          |
        +----------------+-----------------+
                         |
                  Plug-and-play boundary
                         |
        +----------------v-----------------+
        |          CORELESS HUB            |
        | identity / discovery             |
        | capability negotiation           |
        | composition / workload routing   |
        | IPC / fault isolation            |
        +---+---------------+-------------+-+
            |               |             |
       +----v----+      +---v-----+  +---v------+
       |Component|      |Component|  |Component |
       |CPU/AI   |      |Graphics |  |Storage   |
       |VM + AI  |      |VM + AI  |  |VM + AI   |
       +---------+      +---------+  +----------+
```

Every component remains a complete autonomous Coreless computer unit.

## Plug-and-play lifecycle

1. **Connect** — establish the physical or transport link.
2. **Discover** — detect a Coreless identity endpoint.
3. **Verify** — validate Coreless identity and protocol version.
4. **Advertise** — exchange supported capabilities and interface versions.
5. **Negotiate** — select compatible display, input, network, and control channels.
6. **Attach** — bind the Coreless Hub to the host interface.
7. **Boot/Resume** — start or resume the persistent Coreless machine.
8. **Operate** — transport display, input, and network traffic without moving architectural authority to the host.
9. **Detach** — close negotiated channels while preserving Coreless machine state.

## Identity

A plug-and-play Coreless endpoint MUST expose a stable Coreless identity and protocol/version information before higher-level services are enabled.

Identity is separate from host device identity. A host may enumerate the connection, but it does not assign the architectural identity of the Coreless computer.

## Capability negotiation

Capabilities are explicit and versioned. A Coreless endpoint advertises only resources it actually supports.

Negotiation covers at minimum:

- host-interface protocol version
- display transport
- input transport
- network transport
- startup/resume controls
- optional management and telemetry channels

Unsupported capabilities MUST be rejected or omitted rather than silently emulated by host computation.

## Component integration

The host interface attaches to the Coreless composition boundary. It does not flatten autonomous components into host peripherals.

Connected components continue to:

- retain their identities
- run their own Coreless execution boundary
- retain their VM and AI boundaries
- advertise specialized capabilities
- participate in hub workload routing
- remain capable of standalone operation after detachment

## Current implementation status

The repository implements the CorelessHostInterface software contract plus a reference HostTransportAdapter. Implemented coverage includes identity discovery/verification, capability negotiation, attach/detach, Hub binding, lifecycle coordination, channel binding, enumeration, and transport-readiness checks.

The platform-independent discovery layer in `reference/host_discovery.py` now validates transport-neutral identity advertisements and deterministically converts raw discovery candidates into HostEndpoint objects. This layer is deliberately independent of USB, PCIe, Ethernet, SATA, NVMe, or other physical bus enumeration; concrete adapters supply discovery candidates to it.

This is not yet a claim of physical cross-platform plug-and-play. The reference implementation connects concrete in-memory display, input, and network transports to the Coreless boundary without moving Coreless CPU, RAM, VM, OS, AI, or architectural authority into the host.

The remaining transport work is concrete OS/device enumeration and platform adapters. The reference path already covers host transport binding, persistent-system attachment, input event serialization, display scanout delivery, network packet ingress/egress, and transport-neutral discovery validation.


## Transport-neutral identification frame

Coreless-64 defines a transport-neutral identification frame in
`reference/device_protocol.py`. A concrete USB, PCIe, network, or other
adapter can carry this frame without changing the Coreless architectural
identity.

The frame begins with the fixed `CORELS64` magic value and advertises:

- Coreless protocol version
- Coreless-64 architecture identifier
- device type
- capability bitset
- extension payload length
- implementation flags

A host or peer device can therefore identify a Coreless endpoint before
negotiating higher-level display, input, network, startup, or management
channels. The frame is a protocol contract, not a claim that a particular
physical bus has already been implemented.


## Device command protocol

The transport-neutral command frame in `reference/device_command.py`
provides the next layer after device identification. Version 1 defines
correlated commands for:

- capability discovery
- device read
- device write
- execution requests
- status
- synchronization

Each request carries a request identifier so another machine can correlate
responses without depending on the physical transport. Responses retain the
opcode and request identifier and explicitly identify response/error state.

This protocol is deliberately transport-neutral: a physical adapter is
responsible only for carrying command frames and providing the negotiated
transport mechanics.


## Transport session contract

The reference transport layer now defines a reusable `HostTransportSession` for an established endpoint attachment. A session records the endpoint identity, attached Coreless host interface, and negotiated capability set. Session command exchange carries encoded `DeviceCommand` frames without coupling the command path to a particular physical bus.

The reference adapter provides `open_session`, `exchange_session`, `send_session_command`, and `close_session`. Session command replies are required to be response frames with the same request identifier and opcode as the transmitted command; mismatches are rejected at the transport boundary. Closing a session detaches external channels while preserving Coreless machine identity and state. Reopening performs discovery/attachment again rather than transferring computational ownership to the host.

This session layer is transport-neutral and is the software contract immediately above the identity frame and command frame. Physical USB, PCIe, network, and other adapters may implement the same lifecycle.


## Ordered command batches

Version 1 of the reference command layer also supports an ordered CommandBatch. A batch carries up to 256 complete command frames, each prefixed by its encoded frame length. Commands remain individually correlated by request identifier and opcode. A transport adapter may carry the batch as one exchange to reduce per-command transport overhead; it must preserve command order and return one response for each request. Batch validation rejects truncated frames, trailing bytes, oversized batches, and correlation mismatches.
