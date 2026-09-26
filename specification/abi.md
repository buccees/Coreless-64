# Coreless-64 ABI

**Version:** 0.1  
**Status:** Draft

## Purpose

The ABI defines the binary interface between Coreless-64 programs, libraries, operating-system services, and toolchains.

## Initial conventions

The ABI will use the 32 general-purpose registers while assigning conventional roles for:

- integer/pointer arguments
- return values
- temporaries
- callee-saved values
- stack pointer
- frame pointer
- thread-local storage

## Calling convention

The normal function ABI will favor register arguments with stack spill space for overflow.

Return values will use registers where practical.

## Data model

The native 64-bit process model uses:

- 64-bit pointers
- 8-bit bytes
- standard integer widths
- IEEE-oriented floating-point formats

## Binary format

The initial toolchain target will use an ELF-compatible object/executable format unless a later Coreless-native format provides a compelling advantage.

## System calls

The ABI will define a stable system-call boundary independent of the underlying device implementation.

## System calls

The native system-call instruction is `SYSCALL`, encoded as a SYSTEM instruction with function `10`. Its 11-bit immediate selects the system-call number.

A system call traps to the operating-system trap vector with exception cause `0x019` (`syscall`). EPC records the address of the SYSCALL instruction and TVAL records the system-call number.

The initial native system-call namespace is:

| Number | Name | Purpose |
|---:|---|---|
| 0 | exit | terminate the current process |
| 1 | read | read from a file/device handle |
| 2 | write | write to a file/device handle |
| 3 | open | open a filesystem object |
| 4 | close | close a handle |
| 5 | seek | change file position |
| 6 | stat | query filesystem metadata |
| 7 | sleep | suspend the current process |
| 8 | yield | yield execution |
| 9 | spawn | create a process |
| 10 | exec | replace the current process image |
| 11 | wait | wait for a child process |
| 12 | kill | terminate a process |
| 13 | getpid | return current process ID |
| 14 | time | read system time |
| 15 | memory | query memory |
| 16 | cpu_info | query execution contexts |
| 17 | device_info | query devices |
| 18 | net_send | transmit network data |
| 19 | net_recv | receive network data |
| 20 | socket | create a network endpoint |
| 21 | connect | connect an endpoint |
| 22 | listen | listen for connections |
| 23 | accept | accept a connection |
| 24 | display_open | open a display surface/window |
| 25 | display_present | present a display surface |
| 26 | input_read | read input events |
| 27 | checkpoint | request persistent machine-state checkpoint |
| 28 | capability | query architectural/resource capabilities |

Numbers 29–255 are reserved. Numbers 256–2047 are extension-defined.

System calls are an OS boundary, not a hardware-device boundary. An implementation may satisfy the same call using any suitable part of the Coreless computational fabric while preserving the ABI contract.

## Compatibility

Existing application ecosystems will be supported through translation and guest environments rather than by changing the Coreless ABI.


## Native syscall register convention

For the baseline ABI, a syscall uses the immediate encoded in the `SYSCALL` instruction as its syscall number.

- R1: return value
- R2: argument 0
- R3: argument 1
- R4: argument 2
- R5: argument 3
- R6: argument 4
- R7: argument 5

R0 remains hard-wired to zero. A negative R1 denotes an error in the reference ABI implementation. File and device handles are OS-managed opaque values. Memory arguments are virtual addresses in the caller's address space and are subject to normal architectural protection and translation.

The syscall instruction advances past itself on successful OS dispatch; it is not re-executed when the syscall returns.
