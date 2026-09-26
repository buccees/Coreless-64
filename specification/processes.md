# Coreless Process Address Spaces

Each process has an explicit address-space object in the reference runtime. The
reference implementation now gives each process:

- a private page-table root;
- private physical code pages;
- a private physical stack page;
- a common user virtual layout;
- USER privilege while executing;
- MMU translation through its page-table root;
- code mapped read/execute/user and stack mapped read/write/user.

The reference MMU uses the baseline Coreless page-table format described by
the architecture specification. Address-space activation changes ROOT and
ASID, flushes the reference TLB, and enters USER privilege. A process cannot
write its executable code mapping because the page-table entry is read/execute
only.

The current reference memory is still a host-backed byte array. That is the
implementation substrate, not the architectural isolation mechanism: the
architectural boundary is enforced by Coreless virtual translation,
permissions, privilege, and page faults.

## Virtual layout

The bootstrap userspace uses a shared virtual layout so every process can be
linked against the same addresses while each process maps those addresses to
different physical pages.

- user base: `0x10000`
- code: starting at user base, RX/U
- stack: top of the process region, RW/U
- page size: 4 KiB
- baseline process region: 64 KiB, growing for larger programs

This is a bootstrap layout. A future production address-space manager will
add guard pages, shared mappings, copy-on-write, dynamic mappings, and richer
virtual-memory policies.

## Initial userspace

The OS exposes `start_init()` to create the `/init` process as PID 1.
Firmware remains separate from userspace initialization.

The next boot step is to activate PID 1 in USER privilege after firmware and
establish the supervisor trap/syscall path.
