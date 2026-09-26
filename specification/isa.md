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

## Vector and matrix semantic baseline

Status: Draft — hardware-oriented semantic definition

### Vector architectural state

Coreless-64 provides 32 architectural vector registers, `V0`–`V31`. Each vector register has an implementation-defined physical width, reported through the architectural capability interface. The ISA defines vector operations in terms of an architectural vector length (`VL`) and element type rather than a fixed physical lane count.

`VL` is the number of active elements for the current vector operation. Implementations may execute the operation in multiple physical passes when `VL` exceeds native hardware width.

A vector instruction operates on elements `0..VL-1`. Elements outside `VL` are not modified unless an instruction explicitly defines a different behavior.

### Vector masking

Vector instructions that support masking use an architectural mask register. For each element:

- mask bit = 1: the element participates normally;
- mask bit = 0: the destination element is unchanged in merge mode or written as zero in zeroing mode.

Masking never causes inactive elements to perform architectural memory accesses.

An instruction that does not support masking must reject a nonzero mask-control encoding as illegal.

### Vector arithmetic

Integer vector arithmetic is performed independently per element at the selected element width. Signed and unsigned operations are distinct architectural operations.

Unless an instruction explicitly specifies saturation, integer arithmetic wraps modulo `2^N`, where `N` is the element width.

Signed comparisons interpret elements as two's-complement values. Unsigned comparisons interpret elements as unsigned values.

Vector shifts use the element width as the shift domain. Shift counts are reduced according to the operation definition; reserved shift modes are illegal.

### Vector floating-point semantics

FP16, BF16, FP32, and FP64 operations follow the Coreless floating-point environment and IEEE-style exception/rounding behavior defined for the corresponding scalar formats.

FMA operations compute a fused multiply-add where specified: multiplication and addition are performed as one rounded operation.

The instruction's rounding field selects the architectural rounding mode when the operation permits explicit rounding. Otherwise the current floating-point control state applies.

NaNs, infinities, signed zero, underflow, overflow, invalid operation, and inexact behavior are architectural and must not depend on the number of physical vector lanes.

### Vector conversions

Conversion operations explicitly define source and destination element types. Narrowing conversions apply the instruction's rounding and saturation rules. Conversions without saturation use the destination format's defined overflow behavior.

### Vector FMA and reductions

`VFMA`-class operations perform `a*b+c` per active element with fused rounding.

Reduction operations combine active elements in the defined reduction domain. Unless an instruction specifies an associative integer reduction, floating-point reductions must produce an architecturally defined result independent of physical execution width. Implementations must therefore use the specified reduction ordering or an architecturally equivalent method.

### Vector memory operations

Vector loads and stores calculate an address for each active element from the base address plus the operation's addressing mode, stride, index, or descriptor.

Inactive masked elements generate no architectural memory access.

Memory accesses obey Coreless memory ordering rules. Faults, access checks, and translation are performed per architectural access as required by the memory model.

Vector loads/stores may cross cache lines, pages, and implementation-specific internal boundaries. Architectural results and fault behavior must be preserved.

### Matrix/tile architectural state

Coreless-64 defines a matrix/tile register namespace separate from the scalar and vector register files. The initial architectural namespace contains 32 tile/accumulator selectors, `T0`–`T31`. Physical tile dimensions and internal accumulator width are implementation-defined but are exposed through capability discovery.

A matrix instruction operates on an architectural tile shape and element type. The implementation may decompose the operation into any number of physical matrix operations.

### Matrix multiply and accumulate

`MMUL` computes the matrix product `C = A × B` for the dimensions and types encoded by the instruction.

`MMAC` computes `C = (A × B) + C`.

For integer matrix operations, multiplication uses the input element types and accumulation uses the encoded accumulator type. Overflow behavior is defined by the accumulator type and operation mode: wrapping, saturation, or widening must be explicitly encoded by the instruction.

For floating-point matrix operations, accumulation uses the encoded accumulator format and its defined rounding/exception behavior.

### Quantized matrix semantics

Quantized matrix operations interpret input elements according to their encoded signedness and width. Products are accumulated in the encoded accumulator type.

Quantization parameters such as zero points, scale descriptors, clamping bounds, and requantization mode are supplied by the operation's descriptor when required.

Requantization is architectural: the same inputs, descriptors, and architectural floating-point/integer environment must produce the same architectural result on every conforming implementation.

### Matrix shapes and tiles

The encoded tile shape selects an architectural M×N×K operation class. The implementation capability interface reports the native tile shapes it supports.

An implementation may internally split a large architectural tile into smaller operations or combine smaller operations into a larger execution group. This must not change architectural results.

### Matrix memory operations

Tile loads and stores use architectural descriptors to define base address, layout, stride, element type, and tile shape. Implementations may use burst transfers, scratchpad memory, caches, or other mechanisms.

Architectural memory protection, address translation, alignment rules, and faults remain in force for tile accesses.

### Exceptions and retirement

Vector and matrix instructions retire atomically at the architectural instruction level: an instruction either commits its defined architectural effects or takes its defined exception according to the Coreless precise-exception model.

Long-running implementations may execute internally in chunks, but partial internal progress is not architecturally visible as retired state.

### Determinism across implementations

The Coreless ISA specifies mathematical and architectural results, not physical execution width. A 4-lane, 32-lane, FPGA, ASIC, or heterogeneous implementation must produce equivalent architectural results for the same instruction stream and architectural state.

Performance, latency, lane count, tile throughput, cache organization, and physical execution topology are implementation properties unless explicitly exposed through architectural capability state.
