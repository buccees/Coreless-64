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


## Resident-AI role confinement

A component's resident AI is part of that component's virtual-hardware identity; it is
not a general-purpose assistant available to every subsystem. Each component manifest
must declare its role, resident model identity, supported capabilities, and the
explicit AI execution paths it owns. The hub may connect components, but must not
broaden a component's AI authority merely because another model or capability exists
elsewhere in the composed machine.

- **CPU component:** Qwen3 is the primary CPU-intelligence path. It is not a general
  training coordinator and does not inherit chipset, communications, graphics, or
  code-maintenance paths.
- **AI chipset component:** GPT-OSS assists with chipset-facing request interpretation.
  Deterministic chipset logic retains switching, scheduling, authorization, and safety.
- **Reasoning/planning component:** DeepSeek handles only explicitly routed reasoning
  and technical-planning functions. Multiple functions share one model identity.
- **Communication/input component:** Gemma is bound to the communication-facing
  component and its existing host network-adapter path. It handles only declared
  communication/input-interface functions; it is not a fallback for unrelated work.
- **Code/firmware component:** Codestral handles code generation and review only.
  It cannot approve or execute its own proposals.

An execution path is valid only when its declared owner component, resident model,
function assignment, health/lifecycle state, and result provenance all agree. Requests
outside the owning component's declared functions must fail closed or be handed off
explicitly through the Hub to the component that owns that function. The Hub transports
and composes; it does not merge component roles or fan requests out to every AI.

These role assignments are architectural bindings, not proof that the configured model
artifact is installed, reachable, or capability-approved. Live inference evaluation and
physical-device validation remain separate gates.


## Portable component package and reattachment contract

A component is intended to be removable and attachable to a differently configured
Coreless machine. Its identity and specialization travel with the component package;
they must not depend on the source Hub's in-memory registry or on the destination
machine having the same composition.

A portable component package must carry or unambiguously reference:

- stable component identity, package/schema version, and declared hardware role;
- the component's own Coreless executable/VM boundary and persistent state;
- its resident AI binding contract, model/runtime identity, and any required model
  artifact reference or installation manifest;
- role-scoped capabilities and execution-path/function declarations;
- versioned interfaces, resource requirements, and dependency declarations;
- state/configuration migration rules and a compatibility range.

On attachment to a new machine, the Hub must rediscover the component from its own
manifest, validate identity and package integrity, negotiate interface versions and
capabilities, check available resources/dependencies, and create fresh destination-
local runtime bindings. Destination-local object references, registry entries, VM
handles, and transport sessions must never be treated as portable identity. Persisted
configuration must be portable data, not a serialized pointer to an object from the
old machine.

The component keeps its role when the destination is configured differently. The
Hub may negotiate optional capabilities or disable an unavailable function, but it
must not silently reassign the resident AI to unrelated work, borrow another
component's identity, or claim successful attachment when required dependencies are
missing. Required incompatibilities must produce a clear attach failure; optional
capability differences must be reported explicitly. A component can be attached to a
new Hub only after its old Hub attachment and transient channels have been detached.

**Model identity versus function count:** one model identity means one logical model
artifact/runtime identity may serve more than one explicitly declared function within
its component's role. It does not mean the model is welded to one particular machine,
that its in-memory runtime object is portable, or that a destination must expose the
same functions. Reattachment resolves the component's declared model identity against
the destination's available/verified runtime and artifact, then validates the component's
function contract. If the required model is unavailable or incompatible, the component
must remain unready rather than silently substituting another model.
