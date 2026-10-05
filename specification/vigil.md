# VIGIL Optional Input Intelligence Layer

## Purpose

Coreless-64 contains an optional VIGIL layer for spatial and environmental input
interpretation. VIGIL is not a separate runtime dependency of Coreless.

The layer is disabled by default and must never be required for ordinary
pointer, touch, stylus, keyboard, display, or network operation.

## Authority

Coreless remains authoritative for:

- physical host input transport;
- device discovery and identity;
- user-designated pointing-device assignment;
- raw input event ordering;
- input persistence;
- application delivery; and
- enabling or disabling optional VIGIL interpretation.

VIGIL is responsible only for interpreting information supplied by Coreless or
an explicitly attached optional camera source.

VIGIL must not replace or mutate the raw Coreless input stream.

## Input paths

Normal operation:

```
Host device → Coreless input boundary → GUI/applications
```

Optional VIGIL interpretation:

```
Host device → Coreless input boundary → VIGIL → derived interpretation
                                      ↘ raw event remains available
```

Optional camera path:

```
Camera → VIGIL camera source → observation/perception → derived interpretation
```

The camera path is optional. A Coreless machine without a camera remains fully
functional.

## Current implementation boundary

The `vigil/` package provides:

- dependency-free spatial data types;
- camera-frame metadata and ordering;
- observation/detection/track foundations;
- a VIGIL input interpreter compatible with the Coreless input ABI;
- optional enable/disable state;
- optional camera-source polling;
- persistent VIGIL enablement state; and
- deterministic regression tests.

The initial layer deliberately does not invent computer-vision or gesture
results. Camera processing, gesture recognition, object detection, and richer
spatial interpretation will be implemented behind this stable boundary.

## Spatial information

VIGIL uses explicit coordinate frames and preserves:

- source identity;
- timestamps;
- sequence numbers;
- confidence;
- provenance;
- freshness; and
- spatial position where available.

Unknown or unobserved information must not be silently converted into an
asserted world state.

## Future camera capabilities

The layer is designed to support future optional capabilities such as:

- camera-based pointing;
- hand and finger tracking;
- gesture recognition;
- multi-touch-like spatial gestures;
- object/environment observation;
- spatial relationships;
- persistent tracks;
- relevance and priority; and
- attention-aware presentation.

These capabilities must produce information for Coreless rather than taking
authority over Coreless devices or applications.

## Non-goals

VIGIL does not:

- become the Coreless operating system;
- provide CPU, RAM, or host computation;
- replace the Coreless input boundary;
- require a camera;
- require an AI model for basic operation; or
- perform autonomous physical actions.

## Acceptance

The VIGIL layer is acceptable when:

1. Coreless works normally with VIGIL disabled.
2. VIGIL can be enabled without changing the raw input ABI.
3. Derived events retain source identity and source sequence information.
4. Camera input is optional and ordered deterministically.
5. Camera absence does not cause Coreless input failure.
6. Future perception implementations can be added without changing the Coreless
   device-assignment contract.
