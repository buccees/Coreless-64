# Linux TCP Discovery Bootstrap Contract

**Status:** reference implementation added; peer/physical-device interoperability not yet validated  
**Provider:** `reference/linux_host_network.py`

## Scope

The first concrete Linux adapter uses explicitly configured TCP endpoints. This gives the project a testable real-socket path without claiming that Linux can enumerate an unspecified Coreless device over USB, PCIe, or another bus. It does not scan networks or infer identity from an IP address, hostname, or port.

## Bootstrap exchange

The client opens a TCP connection to a configured endpoint and uses the existing `SocketNetworkTransport` 32-bit big-endian length-prefixed packet framing:

1. Client sends one packet whose payload is the exact byte string `CORELESS_DISCOVERY_V1`.
2. Peer responds with one packet containing a complete encoded `DeviceIdentityFrame` from `reference/device_protocol.py`.
3. Client validates the frame structure and UTF-8 identity payload, then submits the identity and live socket-backed network channel to `HostDeviceEnumerator` for the shared Coreless identity/capability checks.
4. The same framed socket remains attached as the network channel after discovery. It is not silently replaced by a memory transport.
5. A malformed or unavailable peer fails discovery and its socket is closed; the provider does not return a partial candidate for that peer.

The peer must advertise the `network` device capability before network negotiation can select it. Host-side capability advertisement is limited to the network channel actually opened by this provider.

## Configuration and failure behavior

- Endpoints are explicit `(host, port)` entries; no broadcast, port scan, DNS identity inference, or implicit trust is performed.
- Duplicate configured endpoints and invalid ports are rejected before connecting.
- Connect and bootstrap reads/writes use a finite timeout.
- Socket framing retains the existing 16 MiB packet ceiling by default.
- A failed or malformed bootstrap closes the socket and propagates an error; callers can decide whether to retry or skip that configured peer.
- TCP reachability is not device authentication. Deployments exposed to untrusted networks still need a defined peer-authentication mechanism before treating identity as trusted.

## Verification limits

Loopback integration tests prove the configured TCP bootstrap, identity-frame validation path, and continued socket channel. They do not prove a real Coreless endpoint implements this exchange, do not provide USB/PCIe enumeration, and do not satisfy physical plug-and-play acceptance. The target peer protocol and authentication policy must be implemented and validated on actual hardware before making that claim.
