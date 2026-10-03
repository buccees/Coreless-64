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

This is intentionally an architectural foundation. It does not yet claim that
multiple reference machines share live execution state; that comes in the next
implementation stages.

## Next implementation stages

1. Bind a component to a complete CorelessSystem instance.
2. Persist component identity and specialization in the machine image.
3. Give each component a VM lifecycle and AI-runtime lifecycle.
4. Add hub IPC/resource channels and capability negotiation.
5. Add fault isolation and hot-plug/rejoin semantics.
6. Make a composed hub-backed system execute workloads across components.
7. Connect the architecture to the eventual plug-and-play host computer interface.
