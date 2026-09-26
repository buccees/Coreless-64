# Coreless-64 ISA

**Version:** 0.1  
**Status:** Draft — hardware-oriented baseline

## Purpose

Coreless-64 is the native instruction-set architecture for the Coreless computational machine. It is specified so the same architectural behavior can be implemented by a software reference machine, FPGA/RTL, ASIC/custom silicon, or a future heterogeneous/storage-integrated execution substrate.

> Architecture defines behavior. Implementation defines mechanism.

## Architectural state

- 32 general-purpose 64-bit registers: R0-R31.
- R0 always reads as zero; writes to R0 are discarded.
- Dedicated 64-bit PC.
- Dedicated 64-bit SP.
- 32 × 64-bit floating-point registers for the scalar FP extension.
- 32 scalable vector registers V0-V31.
- Matrix/AI execution context with implementation-discovered physical dimensions.
- Privileged state: exception PC, cause, trap value, translation root, interrupt state, privilege level, CPU ID, machine configuration pointer, and hypervisor state.

## Data model

Baseline Coreless-64 is little-endian.

- byte = 8 bits
- halfword = 16 bits
- word = 32 bits
- doubleword = 64 bits

Naturally aligned accesses are guaranteed. Unsupported misaligned accesses raise an alignment exception.

## Instruction encoding

Coreless-64 uses a variable-length encoding family. The canonical base instruction is 32 bits. Extension encodings provide longer instructions when required.

Instruction addresses are byte addresses. Base instructions are 4-byte aligned. The decoder determines instruction length before interpreting extension fields.

The exact binary opcode map remains a freeze task; this document defines the architectural instruction families and semantics first.

## Hardware-shaped execution

The reference machine models the architectural pipeline:

1. fetch
2. instruction-length detection
3. decode
4. register read
5. address generation
6. execution
7. memory/device access
8. architectural state update
9. exception detection
10. retirement
11. PC update

A faulting instruction does not partially retire architectural state.

## Base integer instructions

Arithmetic:
- ADD rd, rs1, rs2
- SUB rd, rs1, rs2
- MUL rd, rs1, rs2
- DIV rd, rs1, rs2
- UDIV rd, rs1, rs2
- REM rd, rs1, rs2
- UREM rd, rs1, rs2
- NEG rd, rs1

Immediate:
- ADDI rd, rs1, imm
- SUBI rd, rs1, imm
- ANDI rd, rs1, imm
- ORI rd, rs1, imm
- XORI rd, rs1, imm

Logic:
- AND
- OR
- XOR
- NOT

Shifts/rotates:
- SHL
- SHR
- SAR
- ROL
- ROR

Comparisons:
- SLT
- SLTU
- SEQ
- SNE

For 64-bit variable shifts, the low six bits of the shift count are used.

## Loads and stores

Scalar memory operations:

- LD8, LD16, LD32, LD64
- LD8U, LD16U, LD32U
- ST8, ST16, ST32, ST64

Effective address:

effective_address = R[rs1] + sign_extend(immediate)

Loads and stores use the MMU when translation is enabled and are subject to privilege/device rules.

## Control flow

Conditional branches:
- BEQ
- BNE
- BLT
- BGE
- BLTU
- BGEU

Jumps:
- J
- JR

Calls/returns:
- CALL
- CALLR
- RET

CALL writes the address of the following instruction to its link register. The ABI conventionally uses R1 as the link register.

## Atomics and ordering

The coherent memory system provides:

- XCHG
- CAS
- XADD
- XAND
- XOR atomic operation

Ordering modes:
- relaxed
- acquire
- release
- acquire-release
- sequentially consistent

FENCE provides explicit ordering between selected memory-operation classes.

## Exceptions and traps

Initial architectural causes:

- illegal instruction
- privilege violation
- instruction access fault
- data access fault
- page fault
- alignment fault
- arithmetic/divide fault
- breakpoint/debug trap
- system-call trap
- virtualization fault

Exception entry records faulting PC and cause and transfers control to the configured exception vector. RETX returns from the applicable privileged context.

## System/control

- NOP
- HALT
- WAIT
- TRAP imm
- RETX
- FENCE
- TLBFLUSH
- TLBFLUSHVA
- READCSR
- WRITECSR

System operations are privilege checked where required.

## Floating point

FP16, BF16, FP32, and FP64 are architectural targets.

Operations include:
- add/subtract/multiply/divide
- fused multiply-add/subtract
- min/max
- comparisons
- sign operations
- integer/float conversion
- floating-format conversion

Rounding modes, status flags, and exception behavior must be explicitly specified before ISA v1.0.

## Vector

Vector state is scalable. Operations include:
- integer arithmetic and logic
- shifts
- comparisons
- loads/stores
- reductions
- floating point
- FMA
- widening/narrowing
- masked execution

Software discovers the implemented vector length and does not assume a fixed physical width.

## Matrix/AI

The AI extension targets:
- matrix multiply
- matrix multiply-accumulate
- integer dot products
- quantized multiply-accumulate
- FP16/BF16 matrix operations
- FP32 accumulation
- tile load/store
- conversion and saturation

Initial numerical targets are INT8, INT16, INT32 accumulation, FP16, BF16, and FP32.

Physical matrix dimensions are implementation-defined and capability-discovered; architectural semantics remain stable.

## Cryptography

Reserved/optional extensions cover AES-class operations, SHA-class operations, carry-less multiplication, secure random access, and future protected-memory primitives.

## Virtualization

Privileged virtualization operations manage guest CPU state, guest translation, virtual interrupts, and virtual devices.

## Capability discovery

Software can discover:
- ISA revision
- extensions
- vector length
- AI capabilities
- CPU count
- memory topology
- device topology
- virtualization capabilities

Unsupported extension instructions raise an illegal-instruction exception.

## Compatibility

Coreless-64 is the native ISA. x86-64 and ARM64 compatibility is provided above it through dynamic/static translation, emulation, guest operating systems, and virtualization.

## Native hardware requirement

A native Coreless implementation must fetch and execute Coreless-64 instructions using Coreless computational resources. The host processor is not the Coreless CPU.

The reference machine exists to reproduce the behavior that physical hardware must implement.

## ISA v1.0 freeze checklist

Before freeze:
1. exact binary opcode assignments
2. exact bit fields
3. immediate widths/sign rules
4. exception priority
5. privilege requirements
6. memory-ordering semantics
7. FP rounding/exception behavior
8. vector state semantics
9. matrix/AI numerical semantics
10. extension discovery format
11. reset state
12. interrupt entry/return
13. debug behavior
14. machine configuration interface
