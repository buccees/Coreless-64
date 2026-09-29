# Coreless-64 ISA Conformance Matrix

This matrix is the preflight contract for ISA work. New conformance tests should be derived from this document and the implementation's architectural contract before they are added to CI.

| Area | Architectural contract | Reference implementation | Conformance coverage | Status |
|---|---|---|---|---|
| 64-bit GPRs | R0-R31, 64-bit, R0 reads zero | `reference/core.py` | `test_core.py`, `test_isa_batch2.py` | Covered |
| Base ALU | ADD/SUB/MUL/DIV/UDIV/REM/UREM/logic/shifts/comparisons/NEG | `reference/encoding.py`, `reference/core.py` | `test_isa_batch.py`, `test_isa_batch2.py` | Covered |
| Immediate ALU | ADDI/SUBI/ANDI/ORI/XORI | `reference/encoding.py`, `reference/core.py` | `test_isa_batch2.py` | Covered |
| Loads/stores | LD8/16/32/64, unsigned LD8/16/32, ST8/16/32/64 | `reference/encoding.py`, `reference/core.py` | `test_isa_batch2.py`, core tests | Covered |
| Branches | BEQ/BNE/BLT/BGE/BLTU/BGEU | `reference/encoding.py`, `reference/core.py` | `test_isa_batch2.py`, core tests | Covered |
| Jumps/calls | J/JR/CALL/CALLR/RET and reserved fields | `reference/encoding.py`, `reference/core.py` | `test_isa_batch2.py`, core tests | Covered |
| System control | NOP/HALT/WAIT/TRAP/RETX/FENCE/TLB/CSR/SYSCALL | `reference/encoding.py`, `reference/core.py` | `test_isa_batch2.py`, syscall/encoding tests | Covered |
| Syscall encoding | 11-bit immediate; encoder rejects values outside 0..2047 | `encode_syscall` | `test_isa_batch2.py` | Covered |
| Atomics | XCHG/CAS/XADD/XAND/XXOR plus ordering controls | `reference/core.py` | existing conformance/core tests | Covered |
| Variable length | 32-bit base; 64/128-bit extensions; reserved escape rejected | `instruction_length`, `decode_stream` | variable-length and batch tests | Covered |
| Extended headers | Defined classes decode; reserved classes reject; stream decoder exposes framing fields | `decode_extended_header` | batch tests | Covered |
| Scalar FP | FP16/BF16/FP32/FP64 arithmetic, compare, FMA, conversion, rounding/status | `reference/core.py` | scalar FP conformance tests | Covered |
| Vector integer | arithmetic, logic, shifts, compares, select, memory, reductions | `reference/core.py` | vector conformance tests | Covered |
| Vector FP | FP arithmetic, FMA/FMS, conversion, reductions, edge/mask behavior | `reference/core.py` | vector FP tests | Covered |
| Vector memory | contiguous/strided/gather/scatter and precise restart state | `reference/core.py` | vector memory tests | Covered |
| Matrix/AI | MMUL/MMAC/MMDOT/MQUANTMAC/MADD/MSUB/MMULADD/etc. | `reference/core.py` | matrix conformance tests | Covered |
| Shared RAM | One architectural RAM shared by all CPUs | `CorelessMachine` | `test_isa_batch2.py` | Covered |
| CPU identity | CPU ID and machine CPU count are architectural state | `CorelessMachine` | `test_isa_batch2.py` | Covered |
| Checkpoint state | CPU architectural state restored independently | `machine_runtime.py` | `test_isa_batch2.py`, machine tests | Covered |
| Privilege boundaries | Privileged operations trap/reject at lower privilege | `reference/core.py` | TLB/syscall/core tests | Covered |
| VM isolation | Private VM state; same storage does not grant access; explicit IPC/shared-memory authorization | `reference/virtualization.py` | `reference/test_virtualization.py` | Covered |
| OP_VM encoding/dispatch | VM_SEND/VM_RECV/VM_GRANT/VM_REVOKE/VM_SHARE/VM_UNSHARE decode and require hypervisor control | `reference/encoding.py`, `reference/core.py` | `reference/test_virtualization.py` | Covered |

| CSR access map | 32 defined CSRs, access modes, privilege boundaries | `CSR_ACCESS`, `read_csr`, `write_csr` | `test_isa_batch3.py` | Covered |
| Interrupt entry/return | pending/enabled selection, EPC/CAUSE/TVEC, RETX restoration | `request_interrupt`, `_take_interrupt_if_enabled`, `RETX` | `test_isa_batch3.py` | Covered |
| Alignment/fault atomicity | Faulting operations do not partially retire | `reference/core.py` | memory/matrix fault tests | Covered |
| ISA documentation | Behavior and implementation mechanism remain distinct | `specification/isa.md` | review/preflight | Ongoing |
| Native OS/userspace | Full native environment | runtime layers | limited tests | In progress |
| Local intelligence architecture | Local AI assists Coreless management; deterministic CPU/control boundary remains authoritative; no remote AI dependency | planned AI/control runtime | architectural design | Planned |
| AI/tensor runtime | Local model loading and tensor execution using Coreless vector/matrix capabilities | planned AI runtime | not implemented | Planned |
| Transformers compatibility | Supported local Transformer models translated/executed through Coreless tensor runtime | planned compatibility layer | not implemented | Planned |
| Device/driver model | Architectural devices and drivers | runtime/device layers | partial | In progress |

## Preflight rules

Before adding a conformance batch:

1. **Spec first:** identify the exact architectural statement being tested.
2. **Implementation second:** verify the reference implementation's intended mechanism and failure boundary.
3. **Test third:** encode only behavior guaranteed by the contract.
4. **Exception boundary:** distinguish Python/API errors (for example `ValueError`) from architectural traps (for example `IllegalEncoding` or a CPU trap CSR).
5. **Reserved vs unsupported:** test these separately. A reserved encoding is not automatically the same thing as a valid encoding whose operation is unsupported.
6. **Decoder vs execution:** a stream decoder may validate framing while the CPU validates execution-time semantic constraints.
7. **Retirement:** faulting instructions must be checked for architectural state preservation, not just the reported exception.
8. **Batch review:** every new test should map to a row above or add a new row before it is pushed.

The matrix is a planning and review aid; it does not replace the ISA specification.
