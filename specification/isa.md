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
- XXOR

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


## Concrete vector instruction set

| Op | Mnemonic | Semantics |
|---:|---|---|
| 0x00 | VADD | `vd[i] = vs1[i] + vs2[i]` |
| 0x01 | VSUB | `vd[i] = vs1[i] - vs2[i]` |
| 0x02 | VMUL | `vd[i] = vs1[i] * vs2[i]` |
| 0x03 | VDIV | `vd[i] = vs1[i] / vs2[i]` |
| 0x04 | VMIN | element-wise minimum |
| 0x05 | VMAX | element-wise maximum |
| 0x06 | VAND | element-wise bitwise AND |
| 0x07 | VOR | element-wise bitwise OR |
| 0x08 | VXOR | element-wise bitwise XOR |
| 0x09 | VNOT | element-wise bitwise NOT |
| 0x0A | VSHL | logical left shift |
| 0x0B | VSHR | logical right shift |
| 0x0C | VSAR | arithmetic right shift |
| 0x0D | VROL | rotate left |
| 0x0E | VROR | rotate right |
| 0x0F | VCMP_EQ | equality comparison |
| 0x10 | VCMP_LT | signed less-than comparison |
| 0x11 | VCMP_LTU | unsigned less-than comparison |
| 0x12 | VSEL | select between operands using mask |
| 0x13 | VFMA | fused `a*b+c` |
| 0x14 | VFMS | fused `a*b-c` |
| 0x15 | VNEG | arithmetic negation |
| 0x16 | VABS | absolute value |
| 0x17 | VCONV | explicit element-type conversion |
| 0x18 | VREDUCE_ADD | reduction sum to scalar |
| 0x19 | VREDUCE_MIN | reduction minimum |
| 0x1A | VREDUCE_MAX | reduction maximum |
| 0x1B | VREDUCE_AND | reduction AND |
| 0x1C | VREDUCE_OR | reduction OR |
| 0x1D | VREDUCE_XOR | reduction XOR |
| 0x1E | VLOAD | contiguous/strided vector load |
| 0x1F | VSTORE | contiguous/strided vector store |
| 0x20 | VGATHER | indexed vector load |
| 0x21 | VSCATTER | indexed vector store |
| 0x22 | VSHUFFLE | indexed vector permutation |
| 0x23 | VBROADCAST | scalar-to-vector broadcast |
| 0x24 | VEXTRACT | selected element to scalar |
| 0x25 | VINSERT | replace selected element |
| 0x26 | VZERO | zero active destination elements |

All vector operations apply to active elements `0..VL-1`. Masking, element type, rounding, saturation, and conversion behavior come from the instruction's descriptor and the Coreless floating-point environment.

## Concrete matrix/AI instruction set

| Op | Mnemonic | Semantics |
|---:|---|---|
| 0x00 | MMUL | `Tdst = A × B` |
| 0x01 | MMAC | `Tdst = A × B + Tdst` |
| 0x02 | MMDOT | integer dot-product matrix operation |
| 0x03 | MQUANTMAC | quantized multiply-accumulate with descriptor-controlled requantization |
| 0x04 | MADD | element-wise tile addition |
| 0x05 | MSUB | element-wise tile subtraction |
| 0x06 | MMULADD | fused matrix multiply plus tile add |
| 0x07 | MTRANS | logical tile transpose |
| 0x08 | MCONV | tile element-type conversion |
| 0x09 | MLOAD | tile load |
| 0x0A | MSTORE | tile store |
| 0x0B | MZERO | clear tile |
| 0x0C | MBROADCAST | broadcast scalar/vector data into tile |
| 0x0D | MREDUCE | reduce tile to scalar/accumulator |
| 0x0E | MCLAMP | clamp tile values to descriptor bounds |

`MMUL` uses the encoded M/N/K shape and types. `MMAC` accumulates into the existing destination tile. Integer overflow behavior is explicitly selected by the operation descriptor; floating-point accumulation follows the encoded accumulator type and rounding environment.

`MQUANTMAC` is intended for INT8/UINT8 and related quantized workloads. Zero points, scales, saturation, and requantization are architectural descriptor inputs rather than implementation-specific behavior.

### Common instruction invariants

1. A masked-off vector element performs no architectural memory access and does not alter the destination in merge mode.
2. Integer arithmetic wraps unless saturation/widening is explicitly selected.
3. Floating-point FMA operations are fused where specified; no intermediate rounding is permitted.
4. Matrix dimensions and element types are architectural; physical lane/tile width is implementation-defined.
5. Vector and matrix instructions retire according to the Coreless precise-exception model.
6. Undefined operation numbers or unsupported class/format combinations trap as illegal instructions.

## Vector control and matrix architectural state

The vector control state is architectural and includes VL, VSTART, VTYPE, and VCSR. These values participate in precise context management.

The matrix/AI architectural context includes tile state plus capability information required to validate tile shapes, data types, and accumulator modes.

Capability discovery must expose maximum supported vector length, supported tile shapes, supported data types, quantization modes, and optional accumulator formats.

## Scalar and memory instruction families

### Scalar arithmetic family

The base scalar ISA provides integer arithmetic, logical operations, shifts, rotates, comparisons, and immediate forms. Extended scalar operations use the SCALAR extended class.

| Mnemonic | Semantics |
|---|---|
| ADD | `rd = rs1 + rs2` |
| SUB | `rd = rs1 - rs2` |
| MUL | `rd = rs1 * rs2` |
| DIV | signed division |
| UDIV | unsigned division |
| REM | signed remainder |
| UREM | unsigned remainder |
| AND/OR/XOR | bitwise operation |
| NOT | bitwise complement |
| SHL/SHR/SAR | logical/logical/arithmetic shift |
| ROL/ROR | rotate |
| SLT/SLTU | signed/unsigned comparison |
| SEQ/SNE | equality/inequality comparison |
| NEG | two's-complement negation |

Integer arithmetic wraps modulo 2^64 unless an instruction explicitly specifies a wider, trapping, or saturating result.

### Scalar extended operations

Extended scalar operations reserve the SCALAR class for operations requiring more encoding space, including:

- wide multiply and divide;
- population count and bit counting;
- bit-field extraction/insertion;
- carry/borrow arithmetic;
- sign/zero extension and packing;
- atomic helpers not represented by the base ATOMIC class;
- cryptographic-adjacent bit operations that do not require the CRYPTO class.

Undefined SCALAR operations remain reserved.

### Memory operation family

Coreless memory instructions operate on virtual addresses. Effective addresses are computed in 64-bit address space and then passed through the MMU and protection checks.

Base memory widths are 8, 16, 32, and 64 bits. Extended memory operations may support larger transfers, paired values, vector descriptors, and atomic-width accesses.

| Operation | Meaning |
|---|---|
| LOAD | read memory into scalar register |
| STORE | write scalar register to memory |
| VLOAD/VSTORE | vector memory operation |
| MLOAD/MSTORE | matrix/tile memory operation |

Memory accesses must obey alignment rules defined by the memory specification. Misaligned accesses are either supported by the implementation or generate the defined alignment exception; software-visible behavior must be architectural and consistent.

### Memory ordering

Coreless defines explicit ordering primitives. Ordinary loads and stores follow the Coreless memory model. `FENCE` orders memory operations as specified by its predecessor/successor masks. Atomics provide acquire/release/ordered semantics through their operation encoding.

An implementation may reorder, speculate, cache, prefetch, combine, or split memory operations internally provided the architectural memory model is preserved.

### Atomic family

The ATOMIC class provides:

- atomic swap;
- compare-and-swap;
- fetch-add/sub;
- fetch-and/or/xor;
- signed/unsigned min/max;
- load-linked/store-conditional where supported;
- acquire, release, and sequentially consistent ordering modes.

Atomic operations are indivisible with respect to other Coreless observers for the addressed atomic granule.

### Address calculation

Scalar load/store effective address:

`EA = rs1 + sign_extend(immediate)`

Extended addressing may add a scaled index:

`EA = base + (index × scale) + displacement`

Address arithmetic is performed in the 64-bit virtual address domain. Overflow wraps in the address calculation unless the selected addressing mode explicitly requests checked arithmetic.

### Memory exceptions

Memory operations may raise:

- instruction/data access fault;
- page fault;
- protection fault;
- alignment fault;
- translation fault;
- device/access-order exception where defined.

Exceptions are precise at retirement. A faulting scalar instruction does not commit its destination register. Vector and matrix operations follow their family-specific precise-fault rules while preserving the same architectural exception model.

### Cache and persistence abstraction

Cache hierarchy, write buffers, coherence mechanisms, prefetchers, memory controllers, and physical RAM organization are implementation properties.

The architectural memory model does not require a particular cache design. Persistent machine state is separately defined by the Coreless storage architecture.

### Memory ordering and device I/O

Device memory is strongly ordered according to its architectural memory attributes. Fences are required where the device protocol requires explicit visibility ordering.

DMA-capable devices participate in the defined coherence and memory-visibility rules. The exact transport mechanism is implementation-defined.


## System, privilege, interrupt, and trap instruction families

### Privilege domains

Coreless-64 defines four architectural privilege domains:

| Level | Name | Primary responsibility |
|---:|---|---|
| 0 | User | Applications and unprivileged runtime |
| 1 | Supervisor | Operating system kernel |
| 2 | Hypervisor | Virtual-machine management |
| 3 | Machine | Firmware and highest-privilege machine control |

Instructions and CSRs declare the minimum privilege required. Execution below that privilege raises a privilege exception.

### SYSTEM instruction family

The SYSTEM class provides:

| Instruction | Function |
|---|---|
| NOP | architectural no operation |
| HALT | stop the current execution context |
| WAIT | enter interrupt-wait state |
| TRAP | synchronous software trap |
| RETX | return from exception/trap |
| FENCE | memory ordering barrier |
| TLBFLUSH | invalidate applicable translations |
| TLBFLUSHVA | invalidate translation for an address |
| READCSR | read control/status register |
| WRITECSR | write control/status register |

`TRAP` transfers control to the vector selected by the current privilege/trap configuration. `RETX` restores the saved privilege and interrupt state and resumes at the architectural exception PC.

`HALT` is a privileged machine-control operation unless a supervisor policy explicitly delegates it.

`WAIT` does not terminate the context. It suspends execution until an enabled interrupt, reset, or implementation-defined wake event permitted by the architecture occurs.

### Control and status registers

Coreless defines architectural CSR groups for:

- machine configuration and capabilities;
- privilege and status;
- interrupt enable/pending/threshold state;
- exception vectors;
- page-table roots and MMU control;
- timer/counter state;
- CPU identity and topology;
- virtualization state;
- vector state;
- floating-point state;
- security and boot state.

CSR addresses and exact field assignments are architectural and must be reserved before ISA v1.0 freeze. Unimplemented optional CSRs read as defined zero or raise the defined illegal-CSR exception; software must use capability discovery before relying on optional state.

### Exception classes

Architectural synchronous exceptions include:

- illegal instruction;
- illegal or unavailable CSR;
- privilege violation;
- instruction access fault;
- instruction page fault;
- data access fault;
- data page fault;
- alignment fault;
- breakpoint/debug trap;
- arithmetic fault where enabled;
- floating-point exception;
- virtualization fault;
- capability/resource fault;
- machine-check/fatal hardware fault.

Exception state records at minimum the faulting PC, exception cause, fault address/value when applicable, prior privilege state, interrupt state, and translation context required for restart or diagnosis.

### Interrupt classes

Coreless supports:

- software interrupts/IPIs;
- timer interrupts;
- external device interrupts;
- inter-processor interrupts;
- performance/monitor interrupts;
- machine-level fault interrupts.

Interrupts are prioritized by architectural interrupt priority state. A higher-priority pending interrupt may preempt a lower-priority interrupt when enabled by the current privilege domain.

### Precise traps and retirement

Instructions retire in architectural order. A synchronous exception is reported at the instruction that caused it, and no later instruction may have architecturally visible retired state before that faulting instruction.

Long-running vector and matrix operations may execute internally in chunks, but their partial internal progress is not architectural state. `VSTART` provides vector restart information where required.

### Inter-processor interrupts

Every Coreless execution context has an architectural CPU identifier. Software may send an IPI to another execution context through the interrupt-controller interface.

IPI delivery, acknowledgement, masking, and priority are architectural behaviors; physical routing and interrupt fabric topology are implementation properties.

### Timers and counters

Each implementation provides architectural time/counter facilities sufficient for an operating system to schedule execution contexts and measure intervals. Exact frequency is implementation-specific and exposed through capability/timebase state.

Performance counters are optional but capability-discoverable. Their overflow behavior and interrupt delivery are architectural when implemented.

### Context switching

A complete architectural context includes scalar registers, PC/SP, privilege state, MMU state, interrupt state, floating-point state, vector state, mask state, and matrix/AI state when enabled for the context.

An implementation may use lazy save/restore for optional state, but first use must produce architecturally correct state and exceptions.

### Security and machine state

Machine-level state controls boot configuration, security policy, memory-access attributes, and access to implementation resources. Lower privilege levels cannot directly modify machine security state.

Secure boot and attestation mechanisms may be implementation-specific, but any architectural security state exposed to software must have defined access and transition rules.

## Consistency audit status

The ISA document is subordinate to the exact encoding and architectural-state definitions. Any statement marked as a target or requiring v1.0 definition remains provisional until the corresponding encoding, CSR, exception, and reset definitions are frozen.
