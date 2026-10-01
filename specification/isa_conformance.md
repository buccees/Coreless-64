# Coreless-64 ISA Conformance Matrix

This document maps architectural contracts to reference implementation and tests.

| Area | Status |
|---|---|
| 64-bit GPRs / R0 zero | Covered |
| Base ALU and immediate ALU | Covered |
| Loads/stores | Covered |
| Branches/jumps/calls | Covered |
| System control / CSR / syscall | Covered |
| Atomics | Covered |
| Variable-length 32/64/128-bit framing | Covered |
| Extended headers/reserved classes | Covered |
| Scalar FP | Covered |
| Vector integer/FP/memory/reductions | Covered |
| Matrix/AI execution | Covered |
| Shared RAM / CPU identity | Covered |
| Persistent CPU/machine state | Covered |
| Privilege boundaries | Covered |
| VM isolation / IPC / shared memory | Covered |
| Interrupt entry/return | Covered |
| Alignment/fault atomicity | Covered |
| Native OS/userspace | In progress |
| Device/driver model | In progress |
| Local intelligence architecture | Foundation covered |
| Persistent TensorRuntime | Foundation covered |
| Transformer → TensorRuntime routing | Foundation covered |
| **Stable native Coreless tensor/vector/matrix execution API** | **Planned** |
| Live trained-model inference | Not yet validated |

## Preflight rules

1. Spec first: identify the exact architectural statement.
2. Verify implementation mechanism and failure boundary.
3. Test only behavior guaranteed by the contract.
4. Distinguish API errors from architectural traps.
5. Test reserved fields separately from unsupported operations.
6. Separate decoder/framing validation from execution semantics.
7. Verify retirement/state preservation on faults.
8. Map every new conformance batch to this matrix.

The matrix does not replace the normative ISA specification.
