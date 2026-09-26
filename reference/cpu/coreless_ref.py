"""Hardware-shaped Coreless-64 reference CPU.

This is an architectural model, not a conventional VM. It explicitly models
register state, PC, memory, fetch/execute steps, and traps so the behavior can
later be reproduced in RTL/FPGA/ASIC hardware.
"""

from enum import IntEnum

MASK64 = (1 << 64) - 1


class Trap(IntEnum):
    ILLEGAL = 2
    ALIGNMENT = 4
    DIVIDE = 5
    HALT = 0x100


class CPU:
    def __init__(self, memory_size=1024 * 1024):
        self.regs = [0] * 32
        self.pc = 0
        self.sp = memory_size
        self.memory = bytearray(memory_size)
        self.halted = False
        self.trap = None
        self.cause_pc = 0

    def read_reg(self, index):
        return 0 if index == 0 else self.regs[index]

    def write_reg(self, index, value):
        if index != 0:
            self.regs[index] = value & MASK64

    def _check(self, address, size):
        if address < 0 or address + size > len(self.memory):
            raise MemoryError("Coreless memory access fault")

    def load64(self, address):
        self._check(address, 8)
        return int.from_bytes(self.memory[address:address + 8], "little")

    def store64(self, address, value):
        self._check(address, 8)
        self.memory[address:address + 8] = (
            (value & MASK64).to_bytes(8, "little")
        )

    def trap_enter(self, cause):
        self.cause_pc = self.pc
        self.trap = cause
        if cause == Trap.HALT:
            self.halted = True

    def step(self, instruction):
        if self.halted:
            return

        old_pc = self.pc
        next_pc = (old_pc + 4) & MASK64
        op = instruction[0]

        try:
            if op == "NOP":
                pass
            elif op == "HALT":
                self.trap_enter(Trap.HALT)
                return
            elif op == "ADD":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) + self.read_reg(rs2))
            elif op == "SUB":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) - self.read_reg(rs2))
            elif op == "MUL":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) * self.read_reg(rs2))
            elif op == "DIV":
                _, rd, rs1, rs2 = instruction
                divisor = self.read_reg(rs2)
                if divisor == 0:
                    self.trap_enter(Trap.DIVIDE)
                    return
                self.write_reg(rd, self.read_reg(rs1) // divisor)
            elif op == "AND":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) & self.read_reg(rs2))
            elif op == "OR":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) | self.read_reg(rs2))
            elif op == "XOR":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) ^ self.read_reg(rs2))
            elif op == "NOT":
                _, rd, rs1 = instruction
                self.write_reg(rd, ~self.read_reg(rs1))
            elif op == "SHL":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) << (self.read_reg(rs2) & 63))
            elif op == "SHR":
                _, rd, rs1, rs2 = instruction
                self.write_reg(rd, self.read_reg(rs1) >> (self.read_reg(rs2) & 63))
            elif op == "ADDI":
                _, rd, rs1, imm = instruction
                self.write_reg(rd, self.read_reg(rs1) + imm)
            elif op == "LD64":
                _, rd, rs1, imm = instruction
                address = (self.read_reg(rs1) + imm) & MASK64
                self.write_reg(rd, self.load64(address))
            elif op == "ST64":
                _, rs1, rs2, imm = instruction
                address = (self.read_reg(rs1) + imm) & MASK64
                self.store64(address, self.read_reg(rs2))
            elif op == "BEQ":
                _, rs1, rs2, offset = instruction
                if self.read_reg(rs1) == self.read_reg(rs2):
                    next_pc = (old_pc + offset) & MASK64
            elif op == "BNE":
                _, rs1, rs2, offset = instruction
                if self.read_reg(rs1) != self.read_reg(rs2):
                    next_pc = (old_pc + offset) & MASK64
            elif op == "J":
                _, offset = instruction
                next_pc = (old_pc + offset) & MASK64
            elif op == "CALL":
                _, rd, offset = instruction
                self.write_reg(rd, next_pc)
                next_pc = (old_pc + offset) & MASK64
            elif op == "JR":
                _, rs1, offset = instruction
                next_pc = (self.read_reg(rs1) + offset) & MASK64
            elif op == "RET":
                next_pc = self.read_reg(1)
            else:
                self.trap_enter(Trap.ILLEGAL)
                return

            self.pc = next_pc
            self.regs[0] = 0

        except MemoryError:
            self.trap_enter(Trap.ALIGNMENT)
        except (IndexError, ValueError):
            self.trap_enter(Trap.ILLEGAL)

    def run(self, program, max_steps=100000):
        steps = 0
        while not self.halted and steps < max_steps:
            instruction = program.get(self.pc)
            if instruction is None:
                self.trap_enter(Trap.ILLEGAL)
                break
            self.step(instruction)
            steps += 1
        return steps
