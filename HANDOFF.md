# Coreless-64 — Handoff for Tomorrow

## Stop point

Work was paused on 2026-09-26 because the GitHub Actions reference test suite was still failing. **Do not continue making incremental fixes blindly.** First inspect the existing failures and stabilize the reference implementation.

Latest CI result:

- **53 passed**
- **6 failed**

Latest failed tests:

1. `test_conformance.py::test_branch_fields_and_signed_offset`
2. `test_core.py::test_immediate_and_memory`
3. `test_core.py::test_branch_and_call`
4. `test_encoding.py::test_branch_register_fields`
5. `test_syscall.py::test_native_syscalls`
6. `test_syscall.py::test_file_network_display_syscalls`

## Work completed before the pause

### Repository / CI

Added:

`.github/workflows/reference-tests.yml`

It runs the reference suite with pytest on pushes and pull requests.

### Process isolation direction

`reference/process.py` was expanded toward actual MMU-backed process isolation.

Current intended model:

- each process has a private page-table root;
- each process gets private physical code pages;
- each process gets a private physical stack page;
- processes use a common user virtual layout;
- processes execute in USER privilege;
- ROOT and ASID are switched with the process;
- the reference TLB is cleared on address-space switches;
- code is mapped RX/U;
- stack is mapped RW/U.

This is still a **bootstrap implementation**, not a finished production MMU/page-table system.

### Syscall ABI

The reference syscall implementation was moved toward a real hardware-shaped ABI.

User memory arguments are intended to be passed as:

- pointer in a register;
- length in another register;
- kernel accesses user memory through the CPU memory/MMU interface.

Paths, network targets, checkpoints, and input buffers were partially converted from Python objects in registers to pointer/length arguments.

### Device IO naming

The original `reference/io.py` conflicted with Python's standard-library `io` module.

It was renamed to:

`reference/device_io.py`

References were updated.

### Other changes attempted

Some encoding, CSR, MMU/TLB, shell, and test compatibility fixes were made. **These should be reviewed rather than assumed correct.** Several of them are directly implicated by the remaining failures.

## Important architectural next step

Once the current 6 failures are understood and the baseline suite is green:

1. Finish page-table-backed process isolation.
2. Make every process execute in USER privilege.
3. Implement the real USER → SUPERVISOR syscall/trap path.
4. Preserve/restore complete CPU + MMU process state.
5. Make PID 1 `/init` actually launch during OS boot.
6. Build a minimal native userspace around that path.
7. Then expand filesystem, networking, graphics, scheduler, and application support.

### Important syscall issue

The current CPU still has a shortcut where `SYSCALL` directly invokes `cpu.syscall_handler` instead of necessarily entering the architectural supervisor trap path.

That should be corrected before treating userspace as genuinely hardware-shaped.

Desired eventual flow:

`USER instruction → SYSCALL → supervisor trap → kernel syscall dispatcher → return value → RETX → USER`

## Important MMU issue

The current reference MMU uses a simple flat page-table convention:

`PTE address = ROOT + VPN * 8`

This was useful as a bootstrap model, but it is not yet a full multi-level page-table implementation.

Do not redesign the Coreless architecture casually. The architecture already specifies virtual memory, permissions, privilege levels, TLB invalidation, page faults, and process isolation. The remaining work is implementation.

## CI discipline for tomorrow

**Do not pile fixes onto a failing run.**

Use this sequence:

1. Reproduce/inspect the six failures.
2. Fix the underlying encoding/core contracts first.
3. Get the baseline reference tests green.
4. Then test process/MMU isolation independently.
5. Then implement the supervisor syscall path.
6. Keep every architectural change covered by a focused test.

The last confirmed CI state was **53 passed / 6 failed**.

## Coreless goal

Keep the project aimed at the actual goal:

> The computational fabric is the computer. Persistent storage carries persistent machine state. The host is the interface to the computer.

The reference software is supposed to be hardware-shaped so that the same architectural behavior can later map to FPGA/RTL/ASIC implementations.

**Resume from here.**
