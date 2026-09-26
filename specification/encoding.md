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

The first implementation will use a simple length-detection mechanism suitable for direct mapping to RTL.

## Instruction-length classes

| Length | Intended use |
|---:|---|
| 32 bits | Base scalar, control-flow, memory, and system instructions |
| 64 bits | Extended scalar/system/memory operations and larger immediates |
| 128 bits | Vector, matrix/AI, compound, and other operand-rich operations |
| Future | Reserved for architectural expansion |

The exact prefix/length encoding is part of the v0.1 binary-format work and must be frozen before ISA v1.0.

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
| 0x0D–0x1E | RESERVED |
| 0x1F | EXTENSION / LENGTH ESCAPE |

The use of an extension/length escape does not imply that all extended instructions must share one fixed length. The escape mechanism identifies that additional encoding information must be fetched and interpreted.

## Base 32-bit formats

The following formats define the initial compact instruction representation. They remain subject to the final length-prefix design.

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

1. instruction-length prefixes are exactly defined;
2. every base bit field is defined;
3. every extended encoding has an exact reconstruction rule;
4. immediate and displacement widths are fixed;
5. alignment rules are fixed;
6. illegal-encoding behavior is fixed;
7. the canonical decoded-instruction record is fixed;
8. conformance tests cover every architectural encoding family.

Until then, new architectural features must not silently depend on undocumented encoding behavior.
