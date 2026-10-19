# Coreless-64 Project Handoff

**Working branch:** `integration/qwen3-cpu-execution-proof`  
**Last updated:** 2026-10-19  
**Current priority:** verify automatic component recognition and continue toward host-visible virtual hardware.

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

## Latest test failure and fix awaiting verification

A GitHub Actions run for commit `e88f1fffb820d349d68531c0c5f6d33f7fdfc4e7` reported **924 passed, 1 failed**. The failure was:

`test_linux_mount_provider_unescapes_mountpoint_spaces`

The Linux mount-field decoder had chained string replacements that did not correctly decode mount-table octal escapes. A fix was committed as:

- Commit: `bf29c8414c4abbaadd29e3bbc9c5eb0f3dcf6ae1`
- Change: decode three-digit octal mount escapes in one pass.
- CI run: https://github.com/buccees/Coreless-64/actions/runs/39265693109
- **Status at handoff:** queued when last checked; do not mark the fix verified until this run completes successfully. If it fails, inspect the actual test log, correct the implementation, and rerun the full suite.

## Remaining engineering work

1. **Verify the octal mount-path fix** using the linked GitHub Actions run and record the final result.
2. **Run and review the complete test suite** after the fix, not only the single regression test.
3. **Wire auto-discovery into the actual integrating runtime/service entry point** so the poller is started and stopped deliberately, with errors observable.
4. **Complete host-facing virtual-device integration.** The bridge's role mapping is not sufficient by itself: validate actual OS device behavior and connect the Linux TAP interface to Coreless's packet-processing path. Implement other OS backends only with their appropriate driver/device interfaces.
5. **Implement safe removal handling** for disappeared media/devices, distinguishing a stable removal from transient enumeration errors and honoring active workload leases.
6. **Validate role and dependency negotiation across machines.** Portable manifests must not carry source-machine runtime pointers, VM handles, or transport sessions. Rebind destination-local runtime/transport state; fail clearly when required dependencies are missing and report optional capabilities that are unavailable.
7. **Prove Qwen3 CPU execution end to end** with a test that distinguishes configuration from actual model inference. A configured model identifier or endpoint alone is not proof of live inference.
8. **Keep claims separated:** committed code, passing automated tests, live model inference, host OS device enumeration, and physical hardware verification are different milestones.

## Acceptance target

On a supported host, mounting or installing a compatible component package should lead to automatic discovery, manifest validation, hardware-role identification, compatibility/dependency checks, and creation of the corresponding supported host-facing virtual-device interface without manual task assignment. The complete Coreless installation must remain a separate architecture from a single component hosted by a regular PC.
