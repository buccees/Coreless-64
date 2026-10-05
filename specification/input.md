# Coreless Input and VIGIL Integration

**Architecture:** Coreless-64  
**Status:** Reference architecture defined; implementation in progress

## Purpose

This specification defines the Coreless input boundary for keyboard, pointer, touch, and stylus devices and the optional VIGIL interpretation layer.

Coreless owns the input boundary, device assignment, event routing, persistence, and application delivery. A host supplies physical input transport only.

VIGIL may interpret Coreless input events into gestures and higher-level intents. VIGIL does not become the physical device, host input authority, or Coreless execution authority.

## Architecture

```text
HOST PHYSICAL DEVICE
        |
        v
HOST INPUT TRANSPORT
        |
        v
CORELESS INPUT BOUNDARY
        |
        +--> raw event stream ----------------------+
        |                                           |
        v                                           |
DESIGNATED DEVICE ROUTER                            |
        |                                           |
        v                                           |
OPTIONAL VIGIL INTERPRETATION                       |
        |                                           |
        +--> interpreted events --------------------+
        |
        v
CORELESS GUI / APPLICATIONS
```

Raw input remains available regardless of whether VIGIL is enabled.

## Input device identity

A device has two identities:

- **Host identity:** identity discovered from the current physical host.
- **Coreless assignment identity:** persistent logical designation used by the Coreless machine.

A persistent designation MUST NOT assume that a physical device identity is portable between unrelated hosts.

A designation can therefore be restored as a preference and rebound to a compatible discovered device after host enumeration.

## Device capabilities

A device advertises capabilities including:

- pointer;
- absolute pointing;
- relative pointing;
- touch;
- multi-touch;
- stylus;
- pressure;
- buttons;
- gesture source capability;
- coordinate dimensions/units where known.

Unsupported capabilities are not synthesized by the host.

## Event ABI

The reference event model uses a versioned, deterministic event structure.

Every event contains:

- ABI version;
- event type;
- device identifier;
- monotonic timestamp;
- sequence number;
- coordinate frame;
- optional x/y position;
- optional contact identifier;
- optional pressure;
- optional button;
- optional metadata.

Event types include:

- `POINTER_MOVE`
- `POINTER_BUTTON`
- `TOUCH_BEGIN`
- `TOUCH_UPDATE`
- `TOUCH_END`
- `STYLUS`
- `DEVICE_STATE`

The event stream records what happened at the input boundary. It does not claim what the event means.

## Device assignment

The Coreless input manager maintains:

- discovered devices;
- device capabilities;
- the logical primary pointing-device assignment;
- current binding;
- assignment generation;
- failover state.

Assignment operations:

1. discover compatible devices;
2. select or restore the logical designation;
3. bind the designation to a discovered compatible device;
4. route events;
5. detach cleanly;
6. rebind after reassignment or host change.

If the designated device disappears, Coreless enters an unbound state rather than silently changing the user's designation. A configured failover policy may explicitly select another compatible device.

## VIGIL boundary

When VIGIL is enabled, Coreless provides the raw event stream plus device/capability context to VIGIL.

VIGIL returns derived events such as:

- normalized input;
- recognized gesture;
- interpreted intent;
- interpretation state.

Derived events retain:

- source device;
- source event sequence;
- timestamps;
- interpretation identifier;
- optional confidence/quality;
- provenance.

Raw input remains authoritative evidence. VIGIL interpretation is derived information.

## Optionality

VIGIL is optional.

The Coreless input path MUST support:

- raw-input-only mode;
- VIGIL-enabled mode;
- VIGIL unavailable mode;
- VIGIL degraded mode;
- VIGIL reconnect;
- device reassignment.

An unavailable VIGIL instance MUST NOT prevent basic pointer/touch operation.

## Coordinate systems

The architecture explicitly distinguishes:

1. host/device coordinates;
2. Coreless input coordinates;
3. display coordinates;
4. VIGIL spatial coordinates.

Conversions are explicit and versioned. Coordinates MUST NOT be silently assumed to share units or origins.

## Persistence

Persistent Coreless machine state may retain:

- logical pointing-device designation;
- input preferences;
- gesture configuration;
- VIGIL enablement;
- interpretation configuration.

The persisted designation is a logical preference, not an assertion that the same physical host device will exist after migration.

## Lifecycle

Input follows the host lifecycle:

```text
Discover
  -> Verify
  -> Advertise capabilities
  -> Negotiate input transport
  -> Discover devices
  -> Restore logical assignment
  -> Bind compatible device
  -> Route raw events
  -> Optionally interpret through VIGIL
  -> Deliver to GUI/applications
  -> Detach
  -> Preserve persistent state
```

## Authority and security

Coreless remains authoritative for:

- input routing;
- device assignment;
- application delivery;
- persistent machine state.

VIGIL is authoritative only for the interpretation it produces.

Neither the host nor VIGIL may silently acquire Coreless CPU, RAM, OS, VM, AI, or architectural authority.

## Reference acceptance requirements

The reference implementation should verify:

- event validation;
- deterministic ordering;
- device capability matching;
- assignment/reassignment;
- failover;
- raw event preservation;
- optional VIGIL routing;
- VIGIL-unavailable fallback;
- coordinate metadata;
- persistent logical assignment;
- attach/detach and resume behavior.
