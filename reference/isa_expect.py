"""Independent architectural expectation helpers for Coreless-64 tests.

These helpers intentionally do not call CorelessCPU or its execution paths.
They provide a small mathematical oracle for scalar arithmetic, branches,
effective addresses, and control-flow targets so conformance tests can derive
expected values instead of hand-entering them.
"""

MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63


def u64(value):
    return value & MASK64


def s64(value):
    value = u64(value)
    return value - (1 << 64) if value & SIGN64 else value


def scalar_binary(name, x, y):
    x, y = u64(x), u64(y)
    if name == "ADD":
        return u64(x + y)
    if name == "SUB":
        return u64(x - y)
    if name == "MUL":
        return u64(x * y)
    if name == "DIV":
        if y == 0:
            raise ZeroDivisionError
        if x == SIGN64 and y == MASK64:
            return SIGN64
        ax, ay = s64(x), s64(y)
        q = (abs(ax) // abs(ay)) * (-1 if (ax < 0) != (ay < 0) else 1)
        return u64(q)
    if name == "UDIV":
        if y == 0:
            raise ZeroDivisionError
        return x // y
    if name == "REM":
        if y == 0:
            raise ZeroDivisionError
        if x == SIGN64 and y == MASK64:
            return 0
        ax, ay = s64(x), s64(y)
        q = (abs(ax) // abs(ay)) * (-1 if (ax < 0) != (ay < 0) else 1)
        return u64(ax - q * ay)
    if name == "UREM":
        if y == 0:
            raise ZeroDivisionError
        return x % y
    if name == "AND":
        return x & y
    if name == "OR":
        return x | y
    if name == "XOR":
        return x ^ y
    if name == "SHL":
        return u64(x << (y & 63))
    if name == "SHR":
        return x >> (y & 63)
    if name == "SAR":
        return u64(s64(x) >> (y & 63))
    if name == "ROL":
        shift = y & 63
        return x if shift == 0 else u64((x << shift) | (x >> (64 - shift)))
    if name == "ROR":
        shift = y & 63
        return x if shift == 0 else u64((x >> shift) | (x << (64 - shift)))
    if name == "SLT":
        return int(s64(x) < s64(y))
    if name == "SLTU":
        return int(x < y)
    if name == "SEQ":
        return int(x == y)
    if name == "SNE":
        return int(x != y)
    raise ValueError(name)


def immediate(name, x, imm):
    x = u64(x)
    return {
        "ADDI": u64(x + imm),
        "SUBI": u64(x - imm),
        "ANDI": x & imm,
        "ORI": x | imm,
        "XORI": x ^ imm,
    }[name]


def branch_target(name, pc, x, y, offset):
    signed_x, signed_y = s64(x), s64(y)
    take = {
        "BEQ": x == y,
        "BNE": x != y,
        "BLT": signed_x < signed_y,
        "BGE": signed_x >= signed_y,
        "BLTU": x < y,
        "BGEU": x >= y,
    }[name]
    return u64(pc + offset) if take else u64(pc + 4)


def jump_target(name, pc, base=0, offset=0):
    if name == "J":
        return u64(pc + base)
    if name in ("JR", "CALLR"):
        return u64(base + offset)
    if name == "RET":
        return u64(base)
    if name == "CALL":
        return u64(pc + base)
    raise ValueError(name)


def effective_address(base, immediate_value):
    return u64(base + immediate_value)


def aligned_memory_size(minimum=4096, page_size=4096):
    """Return the smallest valid page-aligned memory size >= minimum."""
    return ((minimum + page_size - 1) // page_size) * page_size


def fp64_binary(name, a, b, acc=0.0):
    """Independent FP64 oracle for the scalar architectural baseline."""
    import math
    if name == "FADD":
        return a + b
    if name == "FSUB":
        return a - b
    if name == "FMUL":
        return a * b
    if name == "FDIV":
        if b == 0.0:
            if a == 0.0:
                return float("nan")
            return math.copysign(float("inf"), a * b)
        return a / b
    if name == "FMIN":
        return b if math.isnan(a) else a if math.isnan(b) else (-0.0 if a == b == 0.0 else min(a, b))
    if name == "FMAX":
        return b if math.isnan(a) else a if math.isnan(b) else (0.0 if a == b == 0.0 else max(a, b))
    if name == "FFMA":
        return a * b + acc
    if name == "FFMS":
        return acc - a * b
    if name == "FNEG":
        return -a
    if name == "FABS":
        return abs(a)
    raise ValueError(name)


def fp_encode(value, element_type):
    """Encode a Python float into a Coreless FP register payload."""
    import struct
    if element_type == 4:  # FP16
        return int.from_bytes(struct.pack("<e", float(value)), "little")
    if element_type == 5:  # BF16, round FP32 payload to 16 high bits
        raw = int.from_bytes(struct.pack("<f", float(value)), "little")
        low, high = raw & 0xFFFF, raw >> 16
        if low > 0x8000 or (low == 0x8000 and (high & 1)):
            high = (high + 1) & 0xFFFF
        return high
    if element_type == 6:  # FP32
        return int.from_bytes(struct.pack("<f", float(value)), "little")
    if element_type == 7:  # FP64
        return int.from_bytes(struct.pack("<d", float(value)), "little")
    raise ValueError(element_type)


def fp_decode(raw, element_type):
    """Decode a Coreless FP register payload into a Python float."""
    import struct
    if element_type == 4:
        return struct.unpack("<e", (raw & 0xFFFF).to_bytes(2, "little"))[0]
    if element_type == 5:
        return struct.unpack("<f", ((raw & 0xFFFF) << 16).to_bytes(4, "little"))[0]
    if element_type == 6:
        return struct.unpack("<f", (raw & 0xFFFFFFFF).to_bytes(4, "little"))[0]
    if element_type == 7:
        return struct.unpack("<d", (raw & MASK64).to_bytes(8, "little"))[0]
    raise ValueError(element_type)


def fp_word(element_type):
    return element_type << 29
