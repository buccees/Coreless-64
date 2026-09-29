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


def vector_int_binary(name, a, b, bits):
    mask = (1 << bits) - 1
    a &= mask
    b &= mask
    if name == "VADD": return (a + b) & mask
    if name == "VSUB": return (a - b) & mask
    if name == "VMUL": return (a * b) & mask
    if name == "VAND": return a & b
    if name == "VOR": return a | b
    if name == "VXOR": return a ^ b
    if name == "VSHL": return (a << (b & (bits - 1))) & mask
    if name == "VSHR": return a >> (b & (bits - 1))
    if name == "VSAR":
        signed = a - (1 << bits) if a & (1 << (bits - 1)) else a
        return (signed >> (b & (bits - 1))) & mask
    if name == "VSEQ": return int(a == b)
    if name == "VSLT": return int((a - (1 << bits) if a & (1 << (bits - 1)) else a) <
                                  (b - (1 << bits) if b & (1 << (bits - 1)) else b))
    if name == "VSLTU": return int(a < b)
    raise ValueError(name)


def vector_fp_binary(name, a, b, acc=0.0):
    import math
    if name == "VFADD": return a + b
    if name == "VFSUB": return a - b
    if name == "VFMUL": return a * b
    if name == "VFMIN":
        return b if math.isnan(a) else a if math.isnan(b) else (-0.0 if a == b == 0.0 else min(a, b))
    if name == "VFMAX":
        return b if math.isnan(a) else a if math.isnan(b) else (0.0 if a == b == 0.0 else max(a, b))
    if name == "VFFMA": return a * b + acc
    raise ValueError(name)


def vector_reduce(name, values, bits):
    mask = (1 << bits) - 1
    vals = [v & mask for v in values]
    if name == "VREDSUM": return sum(vals) & mask
    if name == "VREDAND":
        r = vals[0]
        for v in vals[1:]: r &= v
        return r
    if name == "VREDOR":
        r = vals[0]
        for v in vals[1:]: r |= v
        return r
    if name == "VREDXOR":
        r = vals[0]
        for v in vals[1:]: r ^= v
        return r
    if name == "VREDMIN":
        return min(v - (1 << bits) if v & (1 << (bits - 1)) else v for v in vals) & mask
    if name == "VREDMAX":
        return max(v - (1 << bits) if v & (1 << (bits - 1)) else v for v in vals) & mask
    raise ValueError(name)


MATRIX_SHAPES = ((2, 2, 2), (4, 4, 4), (8, 8, 8), (8, 16, 16), (16, 8, 16), (16, 16, 16), (32, 8, 16))
MATRIX_TYPE_BITS = (8, 16, 32, 64, 16, 16, 32, 64)


def matrix_shape(shape):
    return MATRIX_SHAPES[shape]


def matrix_decode(value, bits, signed):
    value &= (1 << bits) - 1
    return value - (1 << bits) if signed and value & (1 << (bits - 1)) else value


def matrix_encode(value, bits):
    return value & ((1 << bits) - 1)


def matrix_matmul(a, b, m, n, k, ibits, abits, signed=False, acc=None):
    out = [[0 for _ in range(n)] for _ in range(m)]
    for i in range(m):
        for j in range(n):
            total = 0 if acc is None else matrix_decode(acc[i][j], abits, signed)
            for q in range(k):
                total += matrix_decode(a[i][q], ibits, signed) * matrix_decode(b[q][j], ibits, signed)
            out[i][j] = matrix_encode(total, abits)
    return out


def matrix_elementwise(name, a, b, m, n, ibits, abits, signed=False):
    out = [[0 for _ in range(n)] for _ in range(m)]
    for i in range(m):
        for j in range(n):
            x = matrix_decode(a[i][j], ibits, signed)
            y = matrix_decode(b[i][j], ibits, signed)
            z = x + y if name == "MADD" else x - y
            out[i][j] = matrix_encode(z, abits)
    return out


def matrix_convert(a, m, n, src_bits, dst_bits, signed=False):
    return [[matrix_encode(matrix_decode(a[i][j], src_bits, signed), dst_bits) for j in range(n)] for i in range(m)]


def matrix_reduce(a, m, n, bits, signed=False):
    return sum(matrix_decode(a[i][j], bits, signed) for i in range(m) for j in range(n))


def matrix_clamp(a, m, n, ibits, abits, lo, hi, signed=False):
    return [[matrix_encode(max(lo, min(hi, matrix_decode(a[i][j], ibits, signed))), abits) for j in range(n)] for i in range(m)]
