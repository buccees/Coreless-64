# Coreless-64 ISA

**Version:** 0.1  
**Status:** Draft

## Goals

The ISA must be a clean 64-bit general-purpose instruction set that can support operating systems, compilers, browsers, games, scientific software, AI software, and compatibility runtimes.

It must not be a direct copy of x86-64, ARM64, or RISC-V.

## Instruction classes

The initial ISA is organized into:

- integer arithmetic and logic
- shifts and rotates
- comparisons
- branches and control flow
- loads and stores
- atomics
- system/control operations
- floating point
- vector operations
- matrix/AI operations
- memory barriers
- cryptographic operations
- virtualization operations

## Instruction width

Coreless-64 will use a compact variable-length encoding family so common instructions remain compact while larger instructions and future extensions have room to grow.

The canonical base instruction will be 32 bits, with defined extension encodings for longer instructions.

The encoding must preserve simple decode boundaries and permit parallel fetch/decode.

## Load/store model

Memory access is explicit. Arithmetic instructions operate on registers or vector/matrix state.

The base scalar model is load/store.

## Control flow

The ISA provides conditional branches, direct jumps, register-indirect jumps, calls, returns, and a defined mechanism for position-independent code.

## Atomics

Atomic operations will support acquire, release, acquire-release, and sequentially consistent semantics.

## Floating point

FP16, BF16, FP32, and FP64 are architectural targets, including fused multiply-add and conversion operations.

## Vector

Vector operations use scalable vector state and explicit vector-length/masking controls.

## Matrix/AI

Matrix instructions operate on architectural matrix contexts and memory operands with defined layout and accumulation semantics.

## Compatibility

Native Coreless software uses this ISA. x86-64 and ARM64 compatibility is provided above the native ISA through translation, emulation, or guest systems.

## Freeze rule

Before implementation, every opcode, operand encoding, exception behavior, privilege requirement, and memory-ordering behavior must be specified.
