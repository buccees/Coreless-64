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
