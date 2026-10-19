# Coreless-64 Project Handoff

**Working branch:** `integration/qwen3-cpu-execution-proof`  
**Last updated:** 2026-10-19  
**Current priority:** finish the targeted audit of normative specifications and setup/environment instructions. Keep design assignments distinct from artifact-verified capabilities and software/reference evidence distinct from full-machine or physical validation. Once the audit is reconciled, choose the next engineering gate from `REMAINING_REQUIREMENTS.md`; do not implement requirements merely because they appear in documentation.

## Product intent

Coreless-64 is a distinct computer architecture. A regular PC can host individual Coreless software peripherals, but the PC's ordinary operating system must not be confused with the complete Coreless machine. Installing one component should not require a person to manually assign an arbitrary task: Coreless should discover its manifest, identify its declared hardware role, validate compatibility, attach it through Coreless Hub, and request the appropriate host-facing device interface.

The SSD is storage carrying the component package, identity, configuration, and declared dependencies. It does not itself become a physical CPU, GPU, or network adapter merely because the package is stored on it.

## Architecture and role assignments to preserve

- **Qwen3:** primary intelligence for the Coreless CPU; prioritize this integration first.
- **GPT-OSS:** AI service associated with the digital AI chipset; deterministic controller remains authoritative for switching, routing, and safety.
- **DeepSeek:** dedicated reasoning and technical-planning component.
- **Gemma:** dedicated communication/input-interface component, connected to the existing host network adapter; do not redesign the network adapter as a substitute for this connection.
- **Codestral:** code and firmware generation/review component.
- Enforce component AI role/function confinement in executable validation. No general-purpose fallback or silent AI substitution; cross-component work must be an explicit Hub-routed handoff with provenance.
- Avoid requiring all AI models to run concurrently. Keep the main CPU AI integration as the priority.

## Portable components and recognition

The current implementation includes:
- Portable component manifest export/import, with descriptors and declared AI functions.
- Hub attach/detach lifecycle for portable components, including destination-local runtime resolution, dependency checks, activation rollback, and safe detach behavior.
- Manifest discovery from configured mounted roots, including root-level `*.coreless.json` and package-level component manifests.
- A polling auto-discovery service that attaches newly discovered components and can synchronize attached components with a host-device bridge.
- A Linux mounted-volume discovery provider that rereads the mount table and includes configured installation roots.
- A role-aware host virtual-device bridge and a Linux TAP backend for requesting a kernel-visible network interface.

These features are software implementation work; they do **not** yet establish that every host OS natively enumerates all component types as physical hardware.

## Latest test failure and verified fix

A GitHub Actions run for commit `e88f1fffb820d349d68531c0c5f6d33f7fdfc4e7` reported **924 passed, 1 failed**. The failure was:

`test_linux_mount_provider_unescapes_mountpoint_spaces`

The Linux mount-field decoder's regex was matching **two literal backslashes** before the octal digits, but `/proc/*/mounts` contains a single backslash (for example `\040`). The first attempted fix therefore did not match the real input. The corrected regex now matches one backslash and decodes octal escapes in one pass. Fix committed as:

- Failed attempt: `bf29c8414c4abbaadd29e3bbc9c5eb0f3dcf6ae1` (CI run 39265693109 failed: 1 failed, 924 passed).
- Corrective commit: `9d226f90d9ee6d06371de4768900b84247920ac1`; regex now matches the actual single-backslash octal escape.
- Previous failed CI run: https://github.com/buccees/Coreless-64/actions/runs/39265693109
- **Verified result:** [GitHub Actions run 39266027119](https://github.com/buccees/Coreless-64/actions/runs/39266027119) passed **925 tests in 21.49 seconds** on commit `9d226f90d9ee6d06371de4768900b84247920ac1`.

## Remaining engineering work

1. **Finish the documentation audit** by checking the normative specifications and environment/setup instructions for stale status, inconsistent role assignments, and claims stronger than the available evidence. The main overview, handoff, roadmap, requirements, and test guide now carry the current verified checkpoint, but this audit is not yet complete.
2. **Wire auto-discovery into the actual integrating runtime/service entry point** so the poller is started and stopped deliberately, with errors observable.
3. **Complete host-facing virtual-device integration.** The bridge's role mapping is not sufficient by itself: validate actual OS device behavior and connect the Linux TAP interface to Coreless's packet-processing path. Implement other OS backends only with their appropriate driver/device interfaces.
5. **Implement safe removal handling** for disappeared media/devices, distinguishing a stable removal from transient enumeration errors and honoring active workload leases.
6. **Validate role and dependency negotiation across machines.** Portable manifests must not carry source-machine runtime pointers, VM handles, or transport sessions. Rebind destination-local runtime/transport state; fail clearly when required dependencies are missing and report optional capabilities that are unavailable.
7. **Prove Qwen3 CPU execution end to end** with a test that distinguishes configuration from actual model inference. A configured model identifier or endpoint alone is not proof of live inference.
8. **Keep claims separated:** committed code, passing automated tests, live model inference, host OS device enumeration, and physical hardware verification are different milestones.

## Acceptance target

On a supported host, mounting or installing a compatible component package should lead to automatic discovery, manifest validation, hardware-role identification, compatibility/dependency checks, and creation of the corresponding supported host-facing virtual-device interface without manual task assignment. The complete Coreless installation must remain a separate architecture from a single component hosted by a regular PC.
