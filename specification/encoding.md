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
