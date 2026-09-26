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
