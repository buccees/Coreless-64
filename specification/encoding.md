# Coreless-64 Binary Encoding v0.1

Status: Draft — executable binary definition

Coreless-64 is a **64-bit machine architecture**. Instruction encoding is defined independently from the 64-bit architectural data path.

The encoding supports multiple instruction lengths. The base encoding is compact, while longer encodings provide room for extended scalar, vector, matrix/AI, system, and future operations. The instruction length is determined by the decoder before the instruction is interpreted.

## Architectural instruction model

- Architectural GPRs are 64 bits wide.
- PC and SP are 64 bits wide.
- Instruction addresses are byte addresses.
- The architectural instruction stream is little-endian.
- Instructions are naturally aligned according to their encoding length requirements.
- The base instruction encoding is 32 bits.
- Extended encodings may be 64 bits, 128 bits, or future lengths defined by the ISA.
- A 32-bit encoding is **not** the definition of the machine width; it is one instruction representation within the 64-bit architecture.
- Implementations may internally decode an architectural instruction into one or more implementation operations.

The first implementation uses a simple prefix-based length mechanism suitable for direct mapping to RTL. The decoder needs only the first 32-bit instruction word to determine whether the instruction is 32, 64, or 128 bits.

## Instruction-length mechanism

Coreless-64 uses a **prefix-class length mechanism**. Every instruction begins on a 4-byte boundary, and the first 32-bit instruction word contains a 5-bit length class in bits 31:27.

The length class is decoded before the remaining instruction fields are interpreted:

| Bits 31:27 | Meaning | Total instruction length |
|---|---|---:|
| 0x00–0x1C | Base instruction | 32 bits / 4 bytes |
| 0x1D | Extended-64 prefix | 64 bits / 8 bytes |
| 0x1E | Extended-128 prefix | 128 bits / 16 bytes |
| 0x1F | Escape / future length encoding | Reserved |

This deliberately preserves the existing base instruction formats: base primary opcodes 0x00–0x1C retain their current bit positions.

### Fetch and length detection

The architectural fetch sequence is:

1. Fetch the 32-bit word at PC.
2. Inspect bits 31:27.
3. If the value is 0x00–0x1C, the instruction length is 4 bytes.
4. If the value is 0x1D, fetch one additional 32-bit word; the instruction length is 8 bytes.
5. If the value is 0x1E, fetch three additional 32-bit words; the instruction length is 16 bytes.
6. If the value is 0x1F, enter the reserved/future extension path and do not retire the instruction unless a later ISA revision defines the encoding.

The length decision is therefore independent of the semantic opcode decode. A conforming implementation does not need to inspect an extended instruction's operands or function fields to discover its total length.

### Alignment

- All instruction starts are 4-byte aligned.
- 32-bit instructions occupy one 32-bit word.
- 64-bit instructions occupy two consecutive 32-bit words.
- 128-bit instructions occupy four consecutive 32-bit words.
- Extended instructions do **not** require 8-byte or 16-byte start alignment.
- Branch and jump targets must be 4-byte aligned and must point to an instruction boundary.

This keeps instruction-boundary hardware simple while allowing longer encodings.

### Extended prefix word

For 64-bit and 128-bit instructions, bits 31:27 of the first word are the length class. Bits 26:0 are an extended encoding header whose exact field assignments are defined by the extended instruction format.

The remaining 32-bit words are payload words belonging to the same architectural instruction:

- 64-bit form: prefix word + payload word at PC+4.
- 128-bit form: prefix word + payload words at PC+4, PC+8, and PC+12.

All words use the architectural little-endian byte order.

The extended header may identify the instruction family, sub-operation, operand format, data type, register operands, or other architectural fields. Its exact layout is intentionally separate from the length mechanism so that the length mechanism remains stable as vector, matrix/AI, virtualization, and future instruction families are added.

### Architectural length contract

The decoder must produce the instruction length as part of the canonical decoded instruction record.

The length mechanism is architectural, not an implementation hint. Software-visible instruction addresses, PC advancement, branch/jump targets, exception PCs, debugging information, disassembly, and binary tooling must all observe the same instruction boundaries.

A malformed or truncated extended instruction is illegal and must not retire.

## Primary opcode

The base 32-bit encoding reserves the following primary opcode space:

| Value | Family |
|---:|---|
| 0x00 | ALUR |
| 0x01 | ALUI |
| 0x02 | LOAD |
| 0x03 | STORE |
| 0x04 | BRANCH |
| 0x05 | JUMP |
| 0x06 | SYSTEM |
| 0x07 | ATOMIC |
| 0x08 | FP |
| 0x09 | VECTOR |
| 0x0A | MATRIX |
| 0x0B | CRYPTO |
| 0x0C | VM |
| 0x0D–0x1C | RESERVED |
| 0x1D | EXTENDED-64 LENGTH PREFIX |
| 0x1E | EXTENDED-128 LENGTH PREFIX |
| 0x1F | ESCAPE / FUTURE LENGTH ENCODING |

The use of an extension/length escape does not imply that all extended instructions must share one fixed length. The escape mechanism identifies that additional encoding information must be fetched and interpreted.

## Base 32-bit formats

The following formats define the initial compact 32-bit instruction representation. Their field positions are now stable with respect to the length mechanism: base instructions use primary opcodes 0x00–0x1C, while 0x1D–0x1F are reserved for length/escape handling.

### R-format

- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — rs1
- bits 16:12 — rs2
- bits 11:5 — reserved
- bits 4:0 — funct

Reserved bits must be zero.

### I-format

- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — rs1
- bits 16:12 — funct
- bits 11:0 — signed immediate

The immediate is sign-extended to the architectural operand width.

### Load format

- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — rs1
- bits 16:14 — width
- bits 13:0 — signed immediate

Width:
- 0 = LD8 signed
- 1 = LD16 signed
- 2 = LD32 signed
- 3 = LD64
- 4 = LD8 unsigned
- 5 = LD16 unsigned
- 6 = LD32 unsigned

### Store format

- bits 31:27 — primary opcode
- bits 26:22 — rs2
- bits 21:17 — rs1
- bits 16:14 — width
- bits 13:0 — signed immediate

### Branch format

- bits 31:27 — primary opcode
- bits 26:22 — rs1
- bits 21:17 — rs2
- bits 16:12 — funct
- bits 11:0 — signed byte offset

Branch target: target = PC + sign_extend(offset)

The target must satisfy the alignment requirements of the target instruction encoding.

### Jump format

Direct J and CALL use:
- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — reserved
- bits 16:12 — funct
- bits 11:0 — signed offset

Register-indirect JR and CALLR use:
- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — rs1
- bits 16:12 — funct
- bits 11:0 — signed offset

Target: target = R[rs1] + sign_extend(offset)

RET uses funct 0x04 with its register and offset fields zero.

### System format

- bits 31:27 — primary opcode
- bits 26:22 — rd
- bits 21:17 — rs1
- bits 16:0 — operation-specific operand

The operation defines which fields are used and which must be zero.

## Operation assignments

ALUR funct:
- 0x00 ADD
- 0x01 SUB
- 0x02 MUL
- 0x03 DIV
- 0x04 UDIV
- 0x05 REM
- 0x06 UREM
- 0x07 AND
- 0x08 OR
- 0x09 XOR
- 0x0A NOT
- 0x0B SHL
- 0x0C SHR
- 0x0D SAR
- 0x0E ROL
- 0x0F ROR
- 0x10 SLT
- 0x11 SLTU
- 0x12 SEQ
- 0x13 SNE
- 0x14 NEG

ALUI funct:
- 0x00 ADDI
- 0x01 SUBI
- 0x02 ANDI
- 0x03 ORI
- 0x04 XORI

BRANCH funct:
- 0x00 BEQ
- 0x01 BNE
- 0x02 BLT
- 0x03 BGE
- 0x04 BLTU
- 0x05 BGEU

JUMP funct:
- 0x00 J
- 0x01 CALL
- 0x02 JR
- 0x03 CALLR
- 0x04 RET

SYSTEM funct:
- 0x00 NOP
- 0x01 HALT
- 0x02 WAIT
- 0x03 TRAP
- 0x04 RETX
- 0x05 FENCE
- 0x06 TLBFLUSH
- 0x07 TLBFLUSHVA
- 0x08 READCSR
- 0x09 WRITECSR

## Extended instruction formats

Extended instructions use a common hardware-oriented structure. The first 32-bit word is always the length/header word; subsequent words are payload words belonging to the same architectural instruction.

The length prefix occupies bits 31:27 of the first word:
- 0x1D — 64-bit instruction
- 0x1E — 128-bit instruction

The remaining 27 bits of the first word form the extended header:

| Bits | Field | Width | Purpose |
|---|---|---:|---|
| 26:23 | class | 4 | Major architectural instruction class |
| 22:17 | op | 6 | Operation within the class |
| 16:12 | rd | 5 | Primary destination register |
| 11:7 | rs1 | 5 | Primary source register |
| 6:2 | rs2 | 5 | Primary source register |
| 1:0 | format | 2 | Extended operand/payload format |

The header is fixed-width so RTL can decode length, class, operation, and primary scalar register operands immediately after the first fetch.

### Extended classes

| Class | Value | Purpose |
|---|---:|---|
| SCALAR | 0x0 | Extended integer/scalar operations |
| MEMORY | 0x1 | Rich memory/addressing operations |
| FP | 0x2 | Floating-point operations |
| VECTOR | 0x3 | Scalable vector operations |
| MATRIX | 0x4 | Matrix/AI operations |
| SYSTEM | 0x5 | System, synchronization, and control |
| VM | 0x6 | Virtualization operations |
| CRYPTO | 0x7 | Cryptographic operations |
| DEVICE | 0x8 | Device/accelerator operations |
| RESERVED | 0x9–0xF | Future expansion |

Class values identify architectural instruction families, not required implementation units.

### Format field

| Format | Value | Meaning |
|---|---:|---|
| F0 | 0 | Immediate/control payload |
| F1 | 1 | Extended register/operand payload |
| F2 | 2 | Vector/matrix descriptor payload |
| F3 | 3 | Class-defined payload |

The format field selects payload interpretation without changing total instruction length.

### 64-bit format

A 64-bit instruction contains word 0 at PC and word 1 at PC+4. Word 0 contains the length prefix and extended header. Word 1 is a payload word whose exact fields are determined by class and format.

The sequential boundary is PC + 8 unless the instruction changes control flow.

### 128-bit format

A 128-bit instruction contains words at PC, PC+4, PC+8, and PC+12. Word 0 contains the length prefix and extended header. Words 1–3 form a 96-bit payload.

The payload may contain additional registers, immediates, masks, element types, tile descriptors, strides, addresses, or class-specific control fields.

The sequential boundary is PC + 16 unless the instruction changes control flow.

### Payload reconstruction

Payload words are consumed in increasing address order using the architectural little-endian instruction-stream convention.

For an extended instruction, hardware conceptually performs:

fetch word 0 → determine length → fetch remaining words → assemble architectural instruction → decode payload

The payload is part of the architectural instruction and is not independently decoded as additional instructions.

### Register-file domains

The rd, rs1, and rs2 fields in the common extended header refer to the scalar GPR file unless the selected class/format explicitly defines another register domain.

Vector and matrix/AI instructions may use payload fields to identify vector registers, matrix/tile registers, masks, accumulators, or additional scalar registers.

### Hardware decode contract

A hardware decoder should perform:

PC → fetch word 0 → length detect → fetch payload → header decode → class/op decode → operand decode → execute

Length detection occurs before payload interpretation. An implementation may prefetch into an instruction buffer, but payload words must not be treated as independent instructions once the first word establishes an extended boundary.

### Vector payload encoding

The VECTOR class uses the common extended header with `format=F2` for descriptor-based operations. The 96-bit payload of a 128-bit instruction is divided into three 32-bit words:

| Word | Bits | Field | Purpose |
|---|---|---|---|
| 1 | 31:27 | vd2 | Additional vector destination/register selector |
| 1 | 26:22 | vs3 | Third vector source |
| 1 | 21:17 | vm | Mask register |
| 1 | 16:14 | element type | Element width/data type |
| 1 | 13:11 | operation mode | Lane/width behavior |
| 1 | 10:8 | rounding | Floating-point rounding mode |
| 1 | 7:0 | vector flags | Saturation, masking, reduction, and reserved controls |
| 2 | 31:0 | immediate/descriptor low | Stride, index, offset, or operation-specific operand |
| 3 | 31:0 | immediate/descriptor high | Upper operand or operation-specific descriptor |

The exact interpretation of words 2 and 3 is operation-defined, but their presence and order are architectural.

Vector register numbers are five bits and therefore address 32 architectural vector registers. The vector engine itself is scalable; vector length is an implementation capability discovered through the architectural configuration interface rather than encoded as a fixed physical register width.

Element type encodings initially reserve:

| Value | Type |
|---:|---|
| 0 | INT8 |
| 1 | INT16 |
| 2 | INT32 |
| 3 | INT64 |
| 4 | FP16 |
| 5 | BF16 |
| 6 | FP32 |
| 7 | FP64 |

Values outside this table are reserved.

Vector operations must define whether masking, saturation, reduction, widening, narrowing, and floating-point rounding are applicable. An operation that does not support a selected control must raise an illegal-instruction exception rather than silently ignoring architectural control fields.

### Matrix/AI payload encoding

The MATRIX class uses `format=F2` for matrix/tile descriptor operations. Matrix operations use the same 128-bit extended envelope so hardware can decode the common header identically to vector instructions.

The matrix payload is defined as:

| Word | Bits | Field | Purpose |
|---|---|---|---|
| 1 | 31:27 | tile destination | Destination tile/accumulator selector |
| 1 | 26:22 | tile source A | First source tile selector |
| 1 | 21:17 | tile source B | Second source tile selector |
| 1 | 16:14 | input type | A/B element type |
| 1 | 13:11 | accumulator type | Accumulation/output type |
| 1 | 10:8 | tile shape | Matrix dimensions/shape class |
| 1 | 7:5 | mode | Multiply, MAC, dot, quantized, conversion, etc. |
| 1 | 4:0 | flags | Saturation, rounding, masking, and control |
| 2 | 31:16 | M/N descriptor | Matrix dimension or shape parameters |
| 2 | 15:0 | K descriptor | Reduction dimension or inner product length |
| 3 | 31:0 | auxiliary descriptor | Stride, tile memory descriptor, quantization parameters, or operation-specific data |

Initial matrix data types are:

| Input/accumulator class | Values |
|---|---|
| Integer | INT8, INT16, INT32, INT64 |
| Floating point | FP16, BF16, FP32, FP64 |
| Quantized | UINT8, INT8, UINT16, INT16 |

Matrix operations include matrix multiply, matrix multiply-accumulate, integer dot products, quantized multiply-accumulate, type conversion, tile load/store descriptors, and reduction operations.

The matrix engine must not assume a single physical tile size. `tile shape` identifies an architectural shape class, while the implementation capability determines the maximum native tile dimensions and throughput.

### Vector and matrix execution semantics

Vector and matrix payloads describe architectural operations rather than a mandatory microarchitectural implementation. A conforming implementation may execute them through SIMD lanes, vector pipelines, systolic arrays, tensor units, fused heterogeneous fabrics, or other hardware that preserves architectural results and exception behavior.

Masking is architectural: inactive vector elements do not modify their destination unless an instruction explicitly specifies a different merge/zeroing behavior.

Matrix accumulation is architectural: the accumulator type and overflow/rounding behavior are determined by the instruction encoding and the defined operation semantics, not by the implementation's internal accumulator width.

Vector and matrix instructions may be issued independently, pipelined, fused, or distributed across execution units, provided architectural ordering, memory ordering, exceptions, and retirement semantics are preserved.
### Reserved encodings

Undefined class values, operations, format/class combinations, explicitly reserved fields, and malformed or truncated extended instructions are illegal.

Reserved encoding space permits future expansion without changing the architectural instruction-length mechanism.

## Extended encodings

Extended encodings provide architectural space for operations that cannot be expressed cleanly in the compact base form.

Planned extended families include:
- extended immediates and addresses
- floating point
- scalable vector operations
- matrix/AI operations
- cryptographic operations
- virtualization operations
- richer memory operations
- synchronization and atomics
- future accelerator operations

Vector and matrix/AI instructions may contain additional register identifiers, element types, lengths, masks, tiles, strides, accumulation modes, or other control fields.

The encoding must preserve a clear architectural instruction boundary even when the implementation internally decomposes the instruction.

## Decoder contract

The decoder produces one canonical architectural instruction record containing, as applicable:
- instruction length
- instruction class
- operation
- rd
- rs1
- rs2
- additional operands
- immediate/displacement
- extension fields
- privilege requirement
- memory-access type
- architectural side effects

The reference decoder and eventual hardware decoder must agree on this architectural record.

## Illegal encodings

Undefined primary/function combinations, malformed length prefixes, nonzero reserved fields, unsupported extensions, and privilege violations are illegal.

Illegal instructions do not retire.

## Hardware-oriented execution

The architectural execution sequence is:

PC → fetch → length detection → instruction register → decode → register read → execute/address generation → memory/device access → writeback → retire → next PC

The reference implementation intentionally follows this structure so that its behavior can later be mapped into RTL.

## Freeze rule

This document is **not frozen for ISA v1.0** until:

1. instruction-length classes and prefix behavior are exactly defined;
2. every base bit field is defined;
3. every extended encoding has an exact reconstruction rule;
4. immediate and displacement widths are fixed;
5. alignment rules are fixed;
6. illegal-encoding behavior is fixed;
7. the canonical decoded-instruction record is fixed;
8. conformance tests cover every architectural encoding family.

Until then, new architectural features must not silently depend on undocumented encoding behavior.


### Concrete vector and matrix operation allocation

The VECTOR and MATRIX extended classes use the operation namespaces defined in `specification/isa.md`. Operation numbers are architectural identifiers. Undefined values remain reserved and are illegal until assigned by a future ISA revision.

## Instruction-family payload formats

The extended encoding now assigns each major vector/matrix operation to a defined payload family. The common extended header remains unchanged; family-specific words below define the remaining payload bits.

### V-A: vector arithmetic

Used by `VADD`, `VSUB`, `VMUL`, `VDIV`, `VMIN`, `VMAX`, `VAND`, `VOR`, `VXOR`, `VNOT`, `VSHL`, `VSHR`, `VSAR`, `VROL`, `VROR`, `VNEG`, and `VABS`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:27 | arithmetic mode |
| W1 | 26:24 | rounding mode |
| W1 | 23 | saturate |
| W1 | 22 | mask enable |
| W1 | 21 | mask zeroing |
| W1 | 20:16 | vector source 3 / auxiliary register |
| W1 | 15:0 | immediate / shift control |
| W2 | 31:0 | reserved / operation-specific |
| W3 | 31:0 | reserved / operation-specific |

### V-F: vector floating point

Used by `VFMA`, `VFMS`, and floating-point forms of the arithmetic operations.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:26 | rounding mode |
| W1 | 25:24 | FP exception mode |
| W1 | 23 | mask enable |
| W1 | 22 | mask zeroing |
| W1 | 21:17 | vector source 3 |
| W1 | 16:0 | operation control / reserved |
| W2 | 31:0 | optional immediate / descriptor |
| W3 | 31:0 | optional descriptor |

### V-C: vector compare/select

Used by `VCMP_EQ`, `VCMP_LT`, `VCMP_LTU`, and `VSEL`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:27 | comparison mode |
| W1 | 26 | mask enable |
| W1 | 25 | mask zeroing |
| W1 | 24:20 | predicate register |
| W1 | 19:0 | auxiliary/immediate |
| W2 | 31:0 | optional predicate/descriptor |
| W3 | 31:0 | optional descriptor |

### V-R: vector reduction

Used by the `VREDUCE_*` operations.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:27 | reduction mode |
| W1 | 26 | mask enable |
| W1 | 25 | ordered |
| W1 | 24:20 | mask/predicate register |
| W1 | 19:0 | auxiliary control |
| W2 | 31:0 | reduction descriptor |
| W3 | 31:0 | reserved |

`ordered=1` requires the architectural reduction order specified by the instruction. For floating-point reductions, this prevents physical lane count from changing the result.

### V-M: vector memory

Used by `VLOAD`, `VSTORE`, `VGATHER`, and `VSCATTER`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:27 | addressing mode |
| W1 | 26 | mask enable |
| W1 | 25 | fault mode |
| W1 | 24:20 | index/stride register |
| W1 | 19:0 | signed immediate |
| W2 | 31:0 | stride/index/descriptor |
| W3 | 31:0 | upper descriptor / reserved |

Addressing modes initially are `0=contiguous`, `1=strided`, `2=indexed`, `3=descriptor`.

`fault mode` is architecturally defined by the memory specification and may select normal precise faulting versus a later explicitly defined fault-suppression mode. Undefined fault modes are illegal.

### V-D: vector data movement

Used by `VSHUFFLE`, `VBROADCAST`, `VEXTRACT`, `VINSERT`, and `VZERO`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:26 | movement mode |
| W1 | 25 | mask enable |
| W1 | 24 | mask zeroing |
| W1 | 23:19 | auxiliary vector register |
| W1 | 18:0 | index/immediate |
| W2 | 31:0 | permutation/descriptor |
| W3 | 31:0 | reserved / extended descriptor |

### M-G: matrix general

Used by `MMUL`, `MMAC`, `MMDOT`, `MADD`, `MSUB`, and `MMULADD`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | input type |
| W1 | 28:26 | accumulator type |
| W1 | 25:23 | tile shape |
| W1 | 22:20 | execution mode |
| W1 | 19 | saturate |
| W1 | 18 | mask enable |
| W1 | 17:13 | tile source/destination extension |
| W1 | 12:0 | operation control |
| W2 | 31:16 | M/N |
| W2 | 15:0 | K |
| W3 | 31:0 | tile layout / stride / quantization descriptor |

`execution mode` selects multiply, accumulate, dot-product, or fused behavior as permitted by the operation.

### M-Q: matrix quantized

Used by `MQUANTMAC`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | input type |
| W1 | 28:26 | accumulator type |
| W1 | 25:23 | quantization mode |
| W1 | 22 | signed A |
| W1 | 21 | signed B |
| W1 | 20 | saturate |
| W1 | 19 | requantize |
| W1 | 18:14 | auxiliary register |
| W1 | 13:0 | control |
| W2 | 31:16 | zero-point A |
| W2 | 15:0 | zero-point B |
| W3 | 31:16 | scale descriptor |
| W3 | 15:0 | clamp/requantization descriptor |

### M-T: matrix transform/conversion

Used by `MTRANS`, `MCONV`, and `MCLAMP`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | source type |
| W1 | 28:26 | destination type |
| W1 | 25:23 | transform mode |
| W1 | 22 | saturate |
| W1 | 21 | rounding enable |
| W1 | 20:16 | auxiliary register |
| W1 | 15:0 | immediate/control |
| W2 | 31:0 | bounds/conversion descriptor |
| W3 | 31:0 | tile layout descriptor |

### M-L: matrix memory

Used by `MLOAD` and `MSTORE`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:26 | layout mode |
| W1 | 25:23 | tile shape |
| W1 | 22 | mask enable |
| W1 | 21 | fault mode |
| W1 | 20:16 | stride register |
| W1 | 15:0 | signed offset |
| W2 | 31:0 | base/stride descriptor |
| W3 | 31:0 | layout/shape descriptor |

### M-D: matrix data movement

Used by `MZERO`, `MBROADCAST`, and `MREDUCE`.

| Payload word | Bits | Field |
|---|---|---|
| W1 | 31:29 | element type |
| W1 | 28:26 | movement/reduction mode |
| W1 | 25 | mask enable |
| W1 | 24 | saturate |
| W1 | 23:19 | auxiliary register |
| W1 | 18:0 | immediate/control |
| W2 | 31:0 | descriptor |
| W3 | 31:0 | reserved / extended descriptor |

### Family rules

1. The common extended header identifies class and operation before the family payload is interpreted.
2. A family may require only a subset of the 96 payload bits; unused bits are reserved and must be zero unless the operation explicitly assigns them.
3. Register fields in the payload extend the common scalar operand namespace without changing the common header.
4. Unsupported element types, rounding modes, shapes, addressing modes, or control combinations are illegal encodings, not implementation-defined behavior.
5. The same family encoding has the same architectural meaning on reference, FPGA, ASIC, and heterogeneous implementations.
6. Payload fields are architectural state inputs; microarchitectural tiling, lane grouping, buffering, and scheduling remain implementation-defined.

## Architectural type, vector, tile, mask, and descriptor encodings

### Element-type encoding

| Value | Type | Width |
|---:|---|---:|
| 0 | INT8 | 8 |
| 1 | INT16 | 16 |
| 2 | INT32 | 32 |
| 3 | INT64 | 64 |
| 4 | FP16 | 16 |
| 5 | BF16 | 16 |
| 6 | FP32 | 32 |
| 7 | FP64 | 64 |

For matrix quantized operations, signedness is supplied separately where required. UINT8, UINT16, and related unsigned forms therefore do not consume additional global type codes.

### Accumulator-type encoding

| Value | Accumulator |
|---:|---|
| 0 | INT32 |
| 1 | INT64 |
| 2 | FP16 |
| 3 | BF16 |
| 4 | FP32 |
| 5 | FP64 |
| 6 | capability-gated extended accumulator |
| 7 | reserved |

### Floating-point rounding modes

| Value | Mode |
|---:|---|
| 0 | RNE — nearest, ties to even |
| 1 | RTZ — toward zero |
| 2 | RDN — toward minus infinity |
| 3 | RUP — toward plus infinity |
| 4 | RMM — nearest, ties to maximum magnitude |
| 5 | DYN — current FP control state |
| 6 | reserved |
| 7 | reserved |

### Vector length model

Coreless uses a scalable architectural vector length. Architectural vector control contains VL (active element count), VSTART (restart element), and VTYPE (current vector configuration). Physical lane count is implementation-defined and discoverable through capabilities.

### Vector mask model

The architectural mask namespace contains M0–M31. Each mask register supplies one predicate bit per active vector element. Mask enable selects the mask; mask zeroing selects merge or zero behavior. Masked-off memory elements perform no architectural memory access.

### Vector operation modes

| Value | Mode |
|---:|---|
| 0 | normal |
| 1 | saturating |
| 2 | widening |
| 3 | narrowing |

### Vector addressing modes

| Value | Mode |
|---:|---|
| 0 | contiguous |
| 1 | strided |
| 2 | indexed |
| 3 | descriptor |

### Fault modes

| Value | Mode |
|---:|---|
| 0 | precise fault |
| 1 | first-fault |
| 2 | no-fault/suppress-fault |
| 3 | reserved |

First-fault and no-fault modes are capability-gated. Unsupported modes are illegal.

### Tile-shape encoding

| Value | Shape class |
|---:|---|
| 0 | 2x2x2 |
| 1 | 4x4x4 |
| 2 | 8x8x8 |
| 3 | 8x16x16 |
| 4 | 16x8x16 |
| 5 | 16x16x16 |
| 6 | 32x8x16 |
| 7 | descriptor-defined |

Shape 7 obtains dimensions from a matrix descriptor and must be capability-validated.

### Matrix execution modes

| Value | Mode |
|---:|---|
| 0 | multiply |
| 1 | multiply-accumulate |
| 2 | integer dot product |
| 3 | quantized MAC |
| 4 | fused multiply-add |
| 5 | element-wise |
| 6 | reduction |
| 7 | reserved |

### Matrix layout encoding

| Value | Layout |
|---:|---|
| 0 | row-major |
| 1 | column-major |
| 2 | row-major transposed |
| 3 | column-major transposed |
| 4 | packed contiguous |
| 5 | interleaved |
| 6 | descriptor-defined |
| 7 | reserved |

### Quantization modes

| Value | Mode |
|---:|---|
| 0 | integer accumulation only |
| 1 | asymmetric zero-point |
| 2 | symmetric zero-point |
| 3 | per-tensor scale |
| 4 | per-channel scale |
| 5 | requantize to destination type |
| 6 | clamp and requantize |
| 7 | reserved |

### Matrix descriptor format

A matrix descriptor is a 128-bit architectural descriptor:

| Word | Bits | Field |
|---|---|---|
| 0 | 31:0 | base address low |
| 1 | 31:0 | base address high |
| 2 | 31:16 | row stride bytes |
| 2 | 15:0 | column stride bytes |
| 3 | 31:24 | M |
| 3 | 23:16 | N |
| 3 | 15:8 | K |
| 3 | 7:4 | element type |
| 3 | 3:0 | layout |

Descriptor-based matrix operations additionally obtain quantization/scaling references through architectural descriptor registers or operation-specific payload fields. Base address is a full 64-bit virtual address and undergoes normal translation and protection checks.

### Descriptor validation

Before retirement, descriptor-based operations validate type, dimensions, layout, strides, addressability, implementation capabilities, and operation/type compatibility. Invalid descriptors raise the defined architectural exception.
## Scalar and memory payload families

### S-A: scalar extended arithmetic

Used by extended SCALAR operations.

| W1 bits | Field |
|---|---|
| 31:29 | operation subtype |
| 28:27 | width/mode |
| 26 | signed |
| 25:24 | rounding/saturation mode |
| 23:19 | auxiliary register |
| 18:0 | immediate/control |

### S-M: extended scalar memory

Used for extended scalar addressing and transfer operations.

| W1 bits | Field |
|---|---|
| 31:29 | transfer width |
| 28:26 | addressing mode |
| 25 | sign/zero extension |
| 24 | alignment override |
| 23:19 | index register |
| 18:0 | displacement |
| W2 | extended stride/index/descriptor |
| W3 | optional descriptor |

### A: atomic payload

Atomic operations use the ATOMIC class.

| W1 bits | Field |
|---|---|
| 31:27 | atomic operation |
| 26:25 | ordering |
| 24 | acquire |
| 23 | release |
| 22 | signed |
| 21:19 | operand mode |
| 18:0 | immediate/control |

Atomic ordering values:

| Value | Ordering |
|---:|---|
| 0 | relaxed |
| 1 | acquire |
| 2 | release |
| 3 | acquire-release |
| 4 | sequentially consistent |

### Memory ordering masks

FENCE predecessor/successor masks identify ordered domains. Initial domains are:

| Bit | Domain |
|---:|---|
| 0 | reads |
| 1 | writes |
| 2 | device reads |
| 3 | device writes |
| 4 | atomics |
| 5 | vector/matrix memory |
| 6 | DMA/device visibility |
| 7 | reserved |

Reserved mask bits must be zero.

## System and privileged payload families

### SYS: system control

| W1 bits | Field |
|---|---|
| 31:27 | system operation |
| 26:24 | required privilege |
| 23 | serializing |
| 22 | interrupt-affecting |
| 21:19 | target/control class |
| 18:0 | operand/CSR/immediate |

System operation values extend the base SYSTEM namespace without changing the common extended header.

### CSR encoding

CSR operations identify a 16-bit architectural CSR number within the payload. The remaining control fields select read/write behavior and operand source.

Undefined CSR numbers are illegal unless the CSR is explicitly optional and its capability is present.

### Trap encoding

Software traps carry a 16-bit trap/service immediate plus optional control bits. The trap cause presented to the handler identifies a software-generated trap rather than a hardware fault.

### Interrupt control encoding

Interrupt enable, pending, priority, vector-base, and target operations are privileged. User mode may only access interrupt state explicitly delegated by the operating system.

### TLB invalidation encoding

`TLBFLUSH` invalidates translations selected by the current privilege/MMU context. `TLBFLUSHVA` additionally supplies a virtual address operand. Hypervisor and machine modes may select guest or global translation domains where virtualization is enabled.

### RETX encoding

`RETX` has no architectural destination register. It restores the saved exception context and resumes execution at the saved exception PC. If the saved context is invalid or the return would violate privilege rules, a return fault is raised.

### WAIT/HALT encoding

`WAIT` enters an interruptible low-activity execution state. `HALT` stops the selected execution context and requires the privilege level defined by the instruction's control field.

### System instruction invariants

1. Privilege violations trap before architectural side effects.
2. Serializing system instructions establish the ordering guarantees specified by the relevant architectural state.
3. CSR writes affecting translation, privilege, interrupt routing, or execution configuration take effect at the defined architectural boundary.
4. Undefined system operations and reserved control combinations are illegal.
5. Trap and interrupt entry preserve sufficient state for precise restart or diagnosis.

## Consistency audit corrections

The architectural ordering namespace reserves five states: relaxed, acquire, release, acquire-release, and sequentially consistent. Any encoding or implementation that uses the older four-value namespace is non-conforming.


## CSR Operand Encoding

For extended SYSTEM instructions with CSR operations, the 16-bit CSR number occupies the low 16 bits of the immediate/control payload. The operation subtype identifies read, write, set, clear, or implementation-defined future CSR operations.

CSR access checks occur before the instruction produces its architectural result. A failed privilege or access check raises the corresponding exception and does not modify the CSR or destination register.


## Extended Encoding Audit Invariant

Every extended instruction has exactly one length class, one common header, and a class-specific payload. Class and operation numbers are allocated from the common header without overlap with the length mechanism. Reserved class, operation, format, and reserved-field values are illegal. An implementation may decode an extended instruction into multiple internal micro-operations, but architectural retirement occurs as one instruction.

The decoder must validate the complete instruction length before interpreting payload fields. A truncated instruction produces an instruction access fault; an architecturally invalid encoding produces an instruction encoding or illegal-instruction fault according to the faulting condition. No partial architectural state may retire from a malformed extended instruction.

## Extended instruction header

The reference encoder exposes the shared extended header fields as `class`, `operation`, `rd`, `rs1`, `rs2`, and `format`. The header occupies the first 32-bit word after selecting the 64-bit or 128-bit length prefix. Classes 0x0 through 0x8 are currently defined as implementation-available class space; class values above 0x8 are reserved. Operation is 6 bits, register fields are 5 bits, and format is 2 bits. The reference decoder validates these structural fields before the execution engine interprets extended semantics.
\n\nThe reference encoding layer exposes a canonical structural record for a complete extended instruction: `length`, `class`, `operation`, `rd`, `rs1`, `rs2`, `format`, and `payload`. `length` is 8 or 16 bytes, and the payload is exactly `length - 4` bytes. Encoding rejects payloads of the wrong size; decoding rejects base instructions, truncated frames, and length mismatches. The record round-trips to the identical architectural byte sequence, providing a single structural representation for later class-specific execution decoding.\n

## Canonical extended instruction record

The reference encoding layer represents each complete extended instruction as one structural record containing the architectural length, common header fields, and payload. The payload is exactly 4 bytes for the 64-bit form and 12 bytes for the 128-bit form.

Common structural validation is performed before class-specific semantic interpretation: class must be 0x0 through 0x8, operation is 6 bits, each common register operand is 5 bits, and format is 2 bits. Reserved values are illegal encodings.

The record is canonical in both directions. Encoding emits the exact architectural byte sequence represented by the record, while decoding reconstructs the same record. Payload words are never treated as independent instructions.


### 64-bit extended FP execution baseline

The reference implementation now executes the 64-bit extended envelope for the FP class (class=0x2, format=F2). Word 0 carries the common extended header and word 1 carries the complete scalar FP descriptor. The supported FP operation namespace is the same 0x00–0x0C namespace used by the scalar FP reference executor.

A valid 64-bit FP instruction retires as one architectural instruction and advances the PC by exactly 8 bytes. Other classes in the 64-bit envelope remain reserved until their payload semantics are explicitly assigned.
