# Coreless Plug-and-Play Host Interface

**Architecture:** Coreless-64  
**Status:** Architectural draft

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

The repository implements the architectural component/hub foundation and its workload-routing semantics.

The plug-and-play host interface is currently a **specified target boundary**, not yet a claim of cross-platform physical enumeration.

Next implementation work is to add a `CorelessHostInterface` software contract covering discovery, identity handshake, capability negotiation, attach/detach, and display/input/network channel binding.
