# VIGIL — Complete Optional Coreless-Native Environment

## Purpose

Coreless-64 contains VIGIL as a **complete optional native environment** for perception, spatial understanding, interaction, attention, presentation, and interpreted input. VIGIL is part of the Coreless machine; it is not a separate runtime project or host-side computer.

VIGIL is disabled by default and must never be required for ordinary Coreless operation. Optional means optional to activate or use, not partial in scope.

## Execution and AI authority

VIGIL uses the existing Coreless execution architecture for CPU, memory, storage, scheduling, persistence, vector/matrix execution, and AI.

**VIGIL does not create or host a second AI system.** All VIGIL AI analysis is submitted through the existing Coreless AI controller/`AICoreRegistry`. The same Coreless AI cores may serve CPU/computational management, Coreless AI workloads, perception, world-model reasoning, spatial reasoning, interaction, and future vision or gesture workloads.

VIGIL cannot grant itself CPU, device, policy, or physical authority.

## Coreless authority

Coreless remains authoritative for:

- physical host input transport;
- device discovery and identity;
- user-designated pointing-device assignment;
- raw input event ordering and preservation;
- input persistence;
- application delivery;
- camera/device transport boundaries;
- execution, storage, memory, and scheduling; and
- enabling or disabling optional VIGIL services.

VIGIL is authoritative only for its own interpretation state and derived perception/interaction results. It must not replace or mutate authoritative raw Coreless input.

## Input paths

Normal operation:

    Host device → Coreless input boundary → GUI/applications

Optional VIGIL interpretation:

    Host device → Coreless input boundary → VIGIL → derived interpretation
                                          ↘ raw event remains authoritative

Optional camera path:

    Camera → Coreless device boundary → VIGIL perception → world/interaction results

A Coreless machine without VIGIL or without a camera remains fully functional.

## Complete VIGIL environment

The native `vigil/` environment is designed to contain the complete VIGIL capability surface, including:

- input interpretation and designated-device awareness;
- camera-frame ingestion and spatial metadata;
- observations, detections, tracks, and temporal state;
- spatial/temporal fusion;
- world-model state and provenance;
- relevance and priority evaluation;
- attention lifecycle and presentation ordering;
- human interaction context;
- authorization boundaries;
- deterministic simulation/replay;
- shared Coreless AI analysis; and
- persistent VIGIL lifecycle/configuration state.

Perception capabilities such as camera pointing, hand/finger tracking, gesture recognition, object/environment observation, and richer spatial relationships are implemented inside this environment as they mature. They do not require a separate VIGIL runtime or separate AI authority.

## Data integrity

VIGIL preserves source identity, timestamps, sequence numbers, confidence, provenance, freshness, and spatial position where available. Unknown or unobserved information must not silently become asserted world state.

Raw Coreless input remains available even when VIGIL produces a derived result.

## Non-goals

VIGIL does not:

- become the Coreless operating system;
- provide a second CPU, RAM, VM, OS, or AI authority;
- replace the Coreless input/device boundary;
- require a camera;
- require AI for basic non-AI input operation; or
- perform autonomous physical actions without Coreless authority and policy.

## Unified event cycle

When VIGIL is enabled and a camera is available, the Coreless-hosted VIGIL
environment may execute one deterministic camera cycle. A single Coreless
camera capture is shared with the low-latency visual-touch path and normal
perception. Perception updates the world model; the same cycle then evaluates
relevance/priority, updates attention, and produces device-independent
presentation state. Visual-touch output is routed through the Coreless input
boundary. Consumers remain optional, and absence of a perception provider or
fast-touch detector does not invalidate the other path.

## Acceptance

The VIGIL environment is acceptable when:

1. Coreless works normally with VIGIL disabled.
2. VIGIL can be enabled without changing the raw Coreless input ABI.
3. All VIGIL AI analysis routes through the existing Coreless AI registry.
4. No second VIGIL model/runtime becomes an architectural authority.
5. Derived events retain source identity and source sequence information.
6. Camera input is optional and ordered deterministically.
7. Camera absence does not cause Coreless input failure.
8. World-model state remains provenance-aware and deterministic.
9. VIGIL services can grow without changing the Coreless device-assignment contract.
10. VIGIL remains optional while its implemented scope remains complete.
