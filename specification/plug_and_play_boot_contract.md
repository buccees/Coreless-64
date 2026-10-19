# Coreless-64 plug-and-play identity and automatic boot contract

## Normative requirement

Coreless-64 must be discoverable by a compatible plug-and-play host as the configured kind of computer/component, rather than being permanently identified as one hard-coded product role. Its identity and advertised role/capabilities must be explicit configuration carried by the canonical machine configuration or persistent image. Changing the configured role must not create a second machine or silently discard the installed system.

When usable power is supplied, the system must automatically enter its power-on lifecycle, perform device discovery and identity/capability negotiation required by the active host interface, initialize the canonical virtual/attached hardware, and boot or resume the configured installed system without requiring a separate manual OS-start command. The desktop is an interface to that same running system, not a second machine.

## Required lifecycle

1. **Power event:** an explicit host power-available/start event begins startup; power loss stops execution safely according to the machine's persistence contract.
2. **Identify:** publish a stable Coreless identity plus configurable device/component role and versioned capabilities.
3. **Discover and negotiate:** enumerate compatible interfaces, verify identity, negotiate supported capabilities, and attach only validated devices.
4. **Initialize:** initialize the canonical machine, motherboard, CPU(s), memory, persistent image, firmware, OS, and required device services in the existing lifecycle.
5. **Boot/resume automatically:** resolve the boot target from persistent boot configuration; boot it when configured, or resume a valid saved state according to the defined boot policy. Missing or invalid boot configuration must produce a visible, actionable failure rather than pretending a usable installed computer started.
6. **Expose the desktop:** attach the desktop renderer to the same canonical running machine and OS runtime.
7. **Persist safely:** retain the existing persistent image as the source of truth. Do not silently create a parallel machine, replace an image, or reset saved state merely to launch the UI.
8. **Detach/shutdown:** detach host I/O without destroying the persistent machine identity or state; explicit shutdown and power loss follow documented persistence semantics.

## Configuration requirements

- Identity, human-readable name, role/personality, and advertised capabilities must be configurable and validated.
- The configured identity/role and boot target must be recoverable from the persistent image and inspectable before startup mutates that image.
- Host transport identity and the machine's persistent identity must be bound together; a host must not be able to silently substitute another component identity.
- Changing the role is a configuration change to the same canonical machine unless the user explicitly requests a distinct machine/image.
- Defaults must be explicit and documented. A launcher must not claim to boot an installed computer if no persistent image or valid boot target has been selected.

## Acceptance tests

- A configured identity and role are discoverable and advertised consistently after reopening the same image.
- Different valid role configurations can be selected without changing CPU/OS/storage authority or creating duplicate runtime instances.
- A power-available/start event triggers the complete initialize → firmware/OS boot-or-resume → desktop-attach path automatically.
- Reopening an existing image preserves its machine identity, boot target, OS files, and saved machine state.
- A missing image, missing boot target, invalid identity, incompatible capabilities, or corrupt image fails explicitly and does not silently overwrite prior state.
- Power interruption and restart recover according to the existing transactional persistent-image contract.
- Tests distinguish reference/simulated plug-and-play from actual physical bus enumeration and power-supply sensing.

## Evidence boundary

The repository has a persistent CorelessSystem lifecycle and reference host transport contracts, but those facts alone do not prove the complete automatic plug-and-play lifecycle. This contract is satisfied only when implementation and end-to-end acceptance tests demonstrate the required path. Software simulation must not be described as physical power sensing or physical bus enumeration.
