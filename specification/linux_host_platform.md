# Linux Host Platform Integration — Initial Target

**Status:** target selected for the first platform-specific implementation pass  
**Target:** Linux userspace on a documented Linux distribution/kernel environment  
**Scope:** concrete host I/O integration for Coreless-64; not a claim of physical plug-and-play completion

## Why Linux first

Linux is the initial host target because it provides explicit userspace interfaces for sockets, device enumeration, input, and display integration. The transport-neutral Coreless contracts remain platform-independent; this decision does not rename or replace existing interfaces and does not preclude later platform providers.

The exact distribution, kernel baseline, privileges, and device/bus are still to be fixed before a physical-hardware acceptance run. Do not infer that arbitrary Linux hosts or hardware are already supported.

## Existing contract boundaries

The implementation must reuse, not bypass, these reference boundaries:

- `reference/host_discovery.py`: `HostDiscoveryProvider`, `HostDiscoveryCandidate`, and `HostDeviceEnumerator` validate and deterministically order candidate endpoints.
- `reference/host_interface.py`: identity verification, protocol-version checks, capability negotiation, attachment, and detach.
- `reference/host_transport.py`: endpoint sessions and channel binding; failed reconnects must not corrupt a live attachment.
- `reference/host_socket.py`: length-prefixed socket packet framing, limits, serialization, and failure retirement.
- `reference/host_io.py`: display, input, and network transport protocols. The included memory transports are test fixtures, not physical adapters.

A platform provider may enumerate candidates only when it can obtain a real, verifiable Coreless identity advertisement and bind the advertised channels to live I/O objects. It must not manufacture identity frames from an OS device name, guess capabilities from a device class, or report a channel as available when no usable channel exists.

## Implementation sequence

1. **Freeze the physical endpoint contract.** Specify how a real Coreless endpoint is located, how the identity frame is exchanged, how endpoint identity is made stable, and which bus/transport carries each capability. Select the first actual device/bus and its permissions.
2. **Implement Linux discovery against that contract.** Enumerate only supported endpoint types, read and validate the actual identity advertisement, map only verified capabilities to channels, reject duplicate/stale endpoint IDs, and make detach/hot-unplug observable.
3. **Implement Linux network I/O.** Adapt real Linux socket endpoints to the existing framed socket transport. Bound connection/read/write behavior, preserve framing, and make closure/reconnect semantics explicit.
4. **Implement display and input adapters.** Choose concrete Linux APIs appropriate to the selected deployment (for example, a defined display stack and input subsystem); define permissions and event/frame conversion. Do not add several competing stacks before one target is selected.
5. **Exercise the whole lifecycle.** Connect → discover → verify identity → negotiate → attach → boot/resume → operate → detach. Inject malformed advertisements, missing channels, permission failures, timeouts, disconnects, hot unplug, and reconnect failures.
6. **Validate on the target machine.** Record OS/kernel, device/bus, permissions, exact test command, observed I/O, and results. Reference tests remain useful but are not physical-platform evidence.

## Non-negotiable architecture rules

- Coreless CPU, memory, VM, OS state, AI execution, capabilities, and authorization remain owned by Coreless.
- The host supplies external transport and physical I/O only; a host adapter must not silently become a substitute Coreless execution path.
- Identity and capabilities must be verified from the endpoint protocol, not inferred from a friendly name or an OS enumeration record.
- Unsupported or unverified hardware must fail closed and remain undiscovered rather than being presented as plug-and-play.
- Platform-specific imports and APIs must be isolated from platform-neutral reference contracts so the latter remain testable on CI runners.
- Every platform claim must be labeled as interface-only, simulated, Linux-host-tested, or physical-device-validated.

## Current blockers before physical implementation

- No concrete physical Coreless endpoint/bus and identity-exchange mechanism has yet been selected in the checked reference boundary.
- The first Linux display stack and input device access policy have not been selected.
- No real target-device lifecycle evidence exists yet.

These are design prerequisites, not reasons to add a simulated provider and call the platform complete. The next code change should follow once the endpoint/bus contract is specified; until then, changes should be limited to platform-neutral validation or documentation.


## Host-visible virtual-device bridge (software integration checkpoint)

`reference/host_device_bridge.py` translates each attached component's declared
hardware role into a stable host-facing device class and delegates registration to
a platform provider. `ComponentAutoDiscoveryService` can invoke this bridge after
Hub discovery, so component recognition does not stop at finding a manifest or
require the user to assign a task manually.

Current role mappings include Coreless CPU, graphics/video, network adapter,
communication/input, storage, AI chipset, reasoning/planning, and code/firmware.
These are Coreless component identities. The reference in-memory provider verifies
the mapping and lifecycle in tests only; it is not an OS device driver.

**Remaining implementation gate:** provide concrete Linux backends that create and
remove actual OS-visible virtual devices for each supported device class, with
appropriate privileges, lifecycle cleanup, and end-to-end tests. Network devices
may use a Linux virtual network interface backend; input, display/graphics, and
storage require their own compatible Linux APIs/drivers. A CPU or AI-chipset
component must not be misrepresented as a physical host CPU/chipset. No claim of
native OS device enumeration is made until a concrete backend and target-machine
test demonstrate it.


## Host-visible virtual-device bridge (software integration checkpoint)

`reference/host_device_bridge.py` translates each attached component's declared
hardware role into a stable host-facing device class and delegates registration to
a platform provider. `ComponentAutoDiscoveryService` can invoke this bridge after
Hub discovery, so component recognition does not stop at finding a manifest or
require the user to assign a task manually.

Current role mappings include Coreless CPU, graphics/video, network adapter,
communication/input, storage, AI chipset, reasoning/planning, and code/firmware.
These are Coreless component identities. The reference in-memory provider verifies
the mapping and lifecycle in tests only; it is not an OS device driver.

**Remaining implementation gate:** provide concrete Linux backends that create and
remove actual OS-visible virtual devices for each supported device class, with
appropriate privileges, lifecycle cleanup, and end-to-end tests. Network devices
may use a Linux virtual network interface backend; input, display/graphics, and
storage require their own compatible Linux APIs/drivers. A CPU or AI-chipset
component must not be misrepresented as a physical host CPU/chipset. No claim of
native OS device enumeration is made until a concrete backend and target-machine
test demonstrate it.


### First concrete Linux device backend: TAP network interface

`LinuxTapHostDeviceProvider` uses the Linux `/dev/net/tun` interface to request a
kernel TAP interface for a declared `network.adapter` component. The resulting
interface has a deterministic name derived from the stable component ID and is
removed when its file descriptor is closed. Creating it requires host permissions
for TAP creation, typically `CAP_NET_ADMIN` or root.

This is the first concrete OS-visible device backend, not completion of the whole
virtual-device system. It creates the kernel network interface but does not yet
forward TAP packets to/from the Coreless network controller; that packet data path
must be implemented and tested before the adapter is usable for Coreless traffic.
Graphics, input, storage, and other device classes still need their own OS backends.
