# Coreless Component and Hub Architecture

## Purpose

Coreless components are complete autonomous Coreless computers, not passive
peripherals. A component may operate by itself, specialize around a role, or
join other components through a Coreless Hub to form a larger unified computer.

This architecture is part of Coreless-64 itself. It is not a separate product or
a replacement for the existing Coreless execution engine.

## Component contract

Every component has a persistent identity and a specialization contract:

- Coreless execution capability
- component-local memory/storage resources
- VM isolation boundary
- component-local AI runtime/model when the role requires intelligence
- declared capabilities
- role/specialization identity
- discovery and communication interface
- health/fault boundary
- ability to operate independently

The AI and VM are integrated into the component architecture. They are not
external services that must be supplied by a larger Coreless system.

A component can therefore be specialized, for example, for:

- CPU/intelligence
- graphics/vision
- storage/memory
- networking/communications
- orchestration
- other future Coreless roles

Specialization must preserve the capabilities required by the component's role.

## Hub contract

A Coreless Hub is the composition boundary between autonomous components.

The hub provides:

1. component discovery
2. identity and capability advertisement
3. connect/disconnect
4. capability aggregation
5. composition into a unified Coreless computer

Connecting a component does not erase its identity or make it a passive device.

## Two operating modes

### Standalone

A component can run without the other components:

component -> local execution + VM + AI + resources

### Unified

Multiple components can connect through a hub:

component A + component B + component C -> Coreless Hub -> unified computer

The unified system can use specialized capabilities from all connected
components while each component retains its own execution and AI boundaries.

## Separation and reconnection

Disconnecting a component must not destroy its local identity, VM, AI state,
or ability to operate independently.

Reconnecting it must allow discovery and composition again.

## AI specialization

Each component may carry a role-specific model or AI runtime. Training,
adaptation, evaluation, and model updates occur inside the component's VM
boundary where appropriate.

The model does not gain architectural authority merely because it is local.
Coreless CPU, VM, capability, and policy controls remain authoritative.

## Hot-plug and fault isolation

Components are hot-pluggable composition members. Disconnecting a component
removes it from hub discovery and revokes its hub IPC channels without deleting
its identity, VM binding, AI binding, or local state. A component can therefore
continue independently and later rejoin the same or another hub.

Fault isolation removes a faulted component from the active composition and
revokes its hub channels. The component retains its identity and can be
recovered explicitly before rejoining. Faulted components cannot be attached
until recovery, preventing an isolated failure from silently re-entering the
unified system.


## Distributed workload execution

The hub can dispatch deterministic workloads by declared capability. A workload
is routed only to a healthy connected component that advertises the required
capability and exposes a local workload executor. This keeps specialization
local while allowing the composed machine to use the combined capabilities of
its components.

Workloads may also be submitted as a pipeline. Each stage is independently
dispatched to the component specializing in that stage's capability, allowing
CPU/intelligence, vision, storage, networking, and future specialists to
cooperate without collapsing their execution boundaries.

Fault-isolated components are excluded from dispatch automatically. If no
healthy component can execute a requested capability, dispatch fails rather
than silently running the work on an unrelated component.

## Current implementation boundary

reference/components.py establishes the first software contract for:

- autonomous component identity
- role/capability declaration
- local AI/VM integration points
- standalone state
- hub discovery
- connect/disconnect
- capability aggregation
- unified composition metadata

The reference implementation now crosses the native CPU/VM execution boundary: a component can execute its bound VM directly, execute through its Hub, and participate in Hub-level multi-vCPU scheduling. The architecture still does not claim physical cross-device execution; that remains an integration target.

## Current implementation stages

1. Component identity and specialization persistence are implemented.
2. VM and AI-runtime lifecycle ownership is implemented, including standalone services inside a Hub lifecycle.
3. Hub IPC/resource channels, capability negotiation, fault isolation, and hot-plug/rejoin semantics are implemented.
4. Composed Hub workloads execute through native CPU/VM boundaries with bounded multi-vCPU scheduling.
5. Reference host-interface and transport contracts are implemented; concrete physical transports remain.

## Plug-and-play host interface

The Coreless Hub is the composition boundary for autonomous Coreless components. A separate host-interface boundary connects the composed Coreless computer to external equipment.

The host interface handles Coreless identity discovery, verification, capability negotiation, attach/detach, and transport for display, input, networking, and startup services. It does not replace component execution or move Coreless computation into the host.

Target lifecycle: **connect → discover → verify → negotiate → attach → boot/resume → operate → detach**.

The host-interface contract is specified in `specification/host_interface.md`.


## External transport session integration

The autonomous component/hub architecture is exposed to external equipment through the separate host transport boundary. A composed Hub may therefore be discovered and attached through a transport-neutral identity and command session while component execution remains inside Coreless.

Transport sessions carry negotiated host services and correlated command frames; they do not turn autonomous components into host peripherals or move CPU, VM, AI, memory, or architectural authority into the host.

## VIGIL operator display architecture

### Target deployment

The intended operator display is a **remote browser session**. A user opens a browser on a separate screen and connects to a VIGIL operator interface served by the Coreless-64 host or its explicitly configured gateway. Do not assume a directly attached HDMI monitor, touchscreen, or local desktop is required.

The Control Room website remains a development, documentation, and configuration surface. It is not, by itself, the production operator display and its browser-local settings must not be described as controlling runtime hardware.

### Responsibility boundaries

- **Coreless/VIGIL runtime:** owns sensor ingestion, event timestamps, track state, fusion results, confidence/uncertainty, provenance, health, and authorization decisions.
- **Operator-display service:** exposes a versioned, typed view of runtime state and accepts only explicitly authorized operator commands. It must not become a second sensor/fusion engine or a separate AI authority.
- **Remote browser client:** renders the server-provided state, supports accessible/responsive layouts, and submits user intent. The client is untrusted: it cannot grant itself permissions or be the source of truth for track, sensor, or authorization state.
- **Existing Coreless AI boundary:** VIGIL analysis continues through the existing Coreless AI registry/controller and Qwen3 integration; display transport does not introduce another AI runtime.

### Session and transport requirements

1. Use HTTPS for browser sessions. Use an authenticated session and server-side authorization for any non-read-only action; never put secrets or long-lived credentials in browser code or URLs.
2. Separate read-only telemetry/view state from commands that change runtime behavior. Validate command schema, capability, scope, freshness, and authorization on the Coreless side.
3. Prefer a push channel such as WebSocket or Server-Sent Events for live state, with a bounded polling fallback where needed. Include sequence/cursor information and source timestamps so reconnects can detect gaps and stale state.
4. Expose explicit connection, last-update, stale/disconnected, and degraded states. A reachable endpoint is not proof that physical sensors are connected or that measurements are valid.
5. Keep provenance, units, calibration status, uncertainty, and modality identity attached to evidence as it crosses the display boundary. Wi-Fi CSI/RF evidence, calibrated ranging, infrared, and acoustic sonar remain distinct modalities.
6. Support responsive desktop and mobile browser layouts, keyboard operation, accessible focus/status announcements, reduced motion, and reconnect without silently resetting operator context.
7. Treat display preferences (layout, visible layers, text size, motion, startup view) as client presentation preferences unless a separately authorized runtime command is explicitly defined. Never label a browser-only preference as a hardware/runtime setting.

### Implementation sequence and acceptance criteria

1. Define the operator view-state and command schemas, including versioning, event sequence, timestamps, freshness, provenance, and authorization outcomes.
2. Implement an authenticated session boundary and read-only telemetry endpoint before enabling runtime-changing commands.
3. Implement the browser renderer and connection lifecycle against deterministic fixtures; then connect it to the actual Coreless/VIGIL runtime.
4. Add authorized commands individually, with server-side policy checks and auditable outcomes.
5. Verify tests for stale/out-of-order events, reconnect and sequence gaps, revoked/expired sessions, unauthorized commands, malformed payloads, and sensor-degraded states.

Acceptance requires that the browser can render actual runtime state over a remote session, clearly reports stale/disconnected feeds, and cannot bypass Coreless authorization. Static mockups or a successful HTTP connection alone do not satisfy this requirement. Physical sensor integration and real-world localization must be verified separately.

This section records the deployment target and architectural constraints; it does not claim that the remote operator display service or live runtime connection has been implemented.

