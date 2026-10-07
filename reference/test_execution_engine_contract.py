"""Execution-engine contract tests.

These tests verify that step outcomes are explicit while preserving the
legacy boolean step() return value.
"""

from core import CorelessCPU


def test_step_result_reports_retirement():
    cpu = CorelessCPU()
    cpu.memory[0:4] = (0).to_bytes(4, "little")
    assert cpu.step() is True
    assert cpu.last_step_result == {
        "event": "retired",
        "pc": 0,
        "cause": None,
        "tval": 0,
    }
    assert cpu.pc == 4
    assert cpu.instret == 1


def test_step_result_reports_halt_at_instruction_pc():
    cpu = CorelessCPU()
    cpu.memory[0:4] = ((6 << 27) | 1).to_bytes(4, "little")
    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "halt"
    assert cpu.last_step_result["pc"] == 0
    assert cpu.last_step_result["cause"] is None
    assert cpu.pc == 4
    assert cpu.halted


def test_step_result_reports_trap_without_retirement():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0
    cpu.memory[0:4] = ((0x1F << 27)).to_bytes(4, "little")
    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "trap"
    assert cpu.last_step_result["pc"] == 0
    assert cpu.last_step_result["cause"] == 0x002
    assert cpu.last_step_result["tval"] == 0
    assert cpu.instret == 0


def test_run_uses_structured_step_result_for_termination():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0
    cpu.memory[0:4] = ((0x1F << 27)).to_bytes(4, "little")
    assert cpu.run(max_steps=10) == 1
    assert cpu.last_step_result["event"] == "trap"


def test_execution_trap_does_not_retire_divide_by_zero():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x100
    cpu.pc = 0
    # DIV x3, x1, x2; x2 is zero, so execution raises an arithmetic trap.
    cpu.r[1] = 123
    cpu.r[2] = 0
    cpu.memory[0:4] = (1 << 22 | 1 << 17 | 2 << 12 | 3).to_bytes(4, "little")

    assert cpu.step() is True
    assert cpu.last_step_result == {
        "event": "trap",
        "pc": 0,
        "cause": 0x00E,
        "tval": 0,
    }
    assert cpu.csrs[0x004] == 0
    assert cpu.pc == 0x100
    assert cpu.instret == 0
    assert cpu.r[3] == 0


def test_retx_restores_trap_context_and_resumes_at_epc():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x100
    cpu.csrs[0x001] = 1
    cpu.memory[0:4] = ((0x1F << 27)).to_bytes(4, "little")
    cpu.memory[0x100:0x104] = ((6 << 27) | 4).to_bytes(4, "little")

    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "trap"
    assert cpu.csrs[0x004] == 0
    assert cpu.pc == 0x100
    assert cpu.instret == 0
    assert cpu.privilege == 3
    assert cpu.csrs[0x001] == 0

    cpu.privilege = 1
    cpu.csrs[0x000] = 1
    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "retired"
    assert cpu.pc == 0
    assert cpu.privilege == 3
    assert cpu.csrs[0x001] == 1
    assert cpu.instret == 1


def _assert_arithmetic_trap_preserves_destination(name):
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x100
    cpu.r[1] = 0x8000000000000000
    cpu.r[2] = 0
    cpu.r[3] = 0xA5A5A5A5A5A5A5A5
    # The encoding family maps the arithmetic mnemonic through decode().
    from encoding import encode
    cpu.load_program(encode((name, 3, 1, 2)))
    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "trap"
    assert cpu.last_step_result["cause"] == 0x00E
    assert cpu.csrs[0x004] == 0
    assert cpu.pc == 0x100
    assert cpu.instret == 0
    assert cpu.r[3] == 0xA5A5A5A5A5A5A5A5


def test_udiv_divide_by_zero_is_precise():
    _assert_arithmetic_trap_preserves_destination("UDIV")


def test_rem_divide_by_zero_is_precise():
    _assert_arithmetic_trap_preserves_destination("REM")


def test_urem_divide_by_zero_is_precise():
    _assert_arithmetic_trap_preserves_destination("UREM")


def test_div_signed_overflow_is_defined_and_retires():
    cpu = CorelessCPU()
    cpu.r[1] = 0x8000000000000000
    cpu.r[2] = 0xFFFFFFFFFFFFFFFF
    cpu.r[3] = 0
    from encoding import encode
    cpu.load_program(encode(("DIV", 3, 1, 2)))
    assert cpu.step() is True
    assert cpu.last_step_result["event"] == "retired"
    assert cpu.r[3] == 0x8000000000000000
    assert cpu.instret == 1
    assert cpu.pc == 4
