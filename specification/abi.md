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

## Compatibility

Existing application ecosystems will be supported through translation and guest environments rather than by changing the Coreless ABI.
