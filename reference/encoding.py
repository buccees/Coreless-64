"""Coreless-64 v0.1 reference encoding helpers.

The architectural machine is 64-bit. Instructions are variable length:
32-bit base instructions plus 64-bit and 128-bit extended forms. Length is
determined from the first 32-bit word before semantic decoding.
"""

MASK32 = 0xffffffff
OP_ALUR=0; OP_ALUI=1; OP_LOAD=2; OP_STORE=3; OP_BRANCH=4; OP_JUMP=5; OP_SYSTEM=6
OP_ATOMIC=7; OP_FP=8; OP_VECTOR=9; OP_MATRIX=10; OP_CRYPTO=11; OP_VM=12
OP_EXT64=0x1d
OP_EXT128=0x1e
OP_ESCAPE=0x1f

ALUR={0:'ADD',1:'SUB',2:'MUL',3:'DIV',4:'UDIV',5:'REM',6:'UREM',7:'AND',8:'OR',9:'XOR',10:'NOT',11:'SHL',12:'SHR',13:'SAR',14:'ROL',15:'ROR',16:'SLT',17:'SLTU',18:'SEQ',19:'SNE',20:'NEG'}
ALUI={0:'ADDI',1:'SUBI',2:'ANDI',3:'ORI',4:'XORI'}
BRANCH={0:'BEQ',1:'BNE',2:'BLT',3:'BGE',4:'BLTU',5:'BGEU'}
JUMP={0:'J',1:'CALL',2:'JR',3:'CALLR',4:'RET'}
SYSTEM={0:'NOP',1:'HALT',2:'WAIT',3:'TRAP',4:'RETX',5:'FENCE',6:'TLBFLUSH',7:'TLBFLUSHVA',8:'READCSR',9:'WRITECSR',10:'SYSCALL'}
VM={0:'VM_SEND',1:'VM_RECV',2:'VM_GRANT',3:'VM_REVOKE',4:'VM_SHARE',5:'VM_UNSHARE'}
LOAD={0:'LD8',1:'LD16',2:'LD32',3:'LD64',4:'LD8U',5:'LD16U',6:'LD32U'}

class IllegalEncoding(ValueError):
    pass

def sext(v,b):
    return v-(1<<b) if v&(1<<(b-1)) else v

def instruction_length_class(w):
    """Return the architectural length class from the first 32-bit word."""
    return (w & MASK32) >> 27

def instruction_length(w):
    """Return the total architectural instruction length in bytes.

    0x00-0x1c are one-word base instructions; 0x1d and 0x1e are
    the 64-bit and 128-bit extended prefixes.  0x1f is reserved.
    """
    cls = instruction_length_class(w)
    if cls <= 0x1c:
        return 4
    if cls == OP_EXT64:
        return 8
    if cls == OP_EXT128:
        return 16
    raise IllegalEncoding('reserved/future length escape')

def encode_r(f,rd,rs1,rs2):
    if isinstance(f, str):
        if f not in ALUR.values():
            raise IllegalEncoding("unknown ALUR operation")
        f = next(k for k, v in ALUR.items() if v == f)
    return ((OP_ALUR<<27)|(rd<<22)|(rs1<<17)|(rs2<<12)|f)&MASK32

def encode_i(f,rd,rs1,imm):
    if isinstance(f, str):
        if f not in ALUI.values():
            raise IllegalEncoding("unknown ALUI operation")
        f = next(k for k, v in ALUI.items() if v == f)
    if not -(1<<11)<=imm<(1<<11):
        raise IllegalEncoding('imm12 out of range')
    return ((OP_ALUI<<27)|(rd<<22)|(rs1<<17)|(f<<12)|(imm&0xfff))&MASK32

def decode(w):
    w&=MASK32
    op=(w>>27)&31
    rd=(w>>22)&31
    rs1=(w>>17)&31
    rs2=(w>>12)&31
    if op in (OP_EXT64,OP_EXT128,OP_ESCAPE):
        raise IllegalEncoding('extended/future instruction requires length-aware decode')
    if op==OP_ATOMIC:
        f=w&0xF
        if f > 10 or ((w>>9)&7) > 4:
            raise IllegalEncoding('bad atomic')
        return ('ATOMIC',rd,rs1,rs2)
    if op==OP_ALUR:
        f=w&31
        if f not in ALUR or ((w>>5)&127):
            raise IllegalEncoding('bad ALUR')
        return (ALUR[f],rd,rs1,rs2)
    if op==OP_ALUI:
        f=(w>>12)&31
        if f not in ALUI:
            raise IllegalEncoding('bad ALUI')
        return (ALUI[f],rd,rs1,sext(w&0xfff,12))
    if op==OP_LOAD:
        width=(w>>14)&7
        if width not in LOAD:
            raise IllegalEncoding('bad load width')
        return (LOAD[width],rd,rs1,sext(w&0x3fff,14))
    if op==OP_STORE:
        width=(w>>14)&7
        if width>3:
            raise IllegalEncoding('bad store width')
        return (['ST8','ST16','ST32','ST64'][width],rd,rs1,sext(w&0x3fff,14))
    if op==OP_BRANCH:
        f=(w>>12)&31
        if f not in BRANCH:
            raise IllegalEncoding('bad branch')
        return (BRANCH[f],rd,rs1,sext(w&0xfff,12))
    if op==OP_JUMP:
        f=(w>>12)&31
        if f not in JUMP:
            raise IllegalEncoding('bad jump')
        if f in (0,1,4) and rs1!=0:
            raise IllegalEncoding('reserved jump field')
        if f==4 and (rd!=0 or (w&0xfff)!=0):
            raise IllegalEncoding('bad RET')
        return (JUMP[f],rd,rs1,sext(w&0xfff,12))
    if op==OP_VM:
        f=w&31
        if f not in VM:
            raise IllegalEncoding('bad VM operation')
        return (VM[f],rd,rs1,rs2)
    if op==OP_SYSTEM:
        f=w&31
        if f not in SYSTEM:
            raise IllegalEncoding('bad system')
        return (SYSTEM[f],rd,rs1,(w>>5)&0x7ff)
    raise IllegalEncoding('unknown primary opcode')

def encode_syscall(number):
    if not 0 <= number < (1 << 11):
        raise ValueError('syscall number out of range')
    return ((OP_SYSTEM << 27) | (10) | (number << 5)) & MASK32

def to_bytes(w):
    return int(w&MASK32).to_bytes(4,'little')

def from_bytes(data):
    if len(data)!=4:
        raise ValueError('base instruction word must be 4 bytes')
    return int.from_bytes(data,'little')



def encode_extended_header(cls, op=0, rd=0, rs1=0, rs2=0, fmt=0, *, length=16):
    """Encode the fixed header shared by Coreless extended instructions."""
    if length not in (8, 16):
        raise IllegalEncoding("invalid extended instruction length")
    prefix = OP_EXT64 if length == 8 else OP_EXT128
    if not 0 <= cls <= 0x8:
        raise IllegalEncoding("reserved extended class")
    if not 0 <= op <= 0x3F:
        raise IllegalEncoding("extended operation out of range")
    for name, value, limit in (
        ("rd", rd, 0x1F), ("rs1", rs1, 0x1F), ("rs2", rs2, 0x1F),
    ):
        if not 0 <= value <= limit:
            raise IllegalEncoding(f"{name} register out of range")
    if not 0 <= fmt <= 0x3:
        raise IllegalEncoding("extended format out of range")
    return (
        (prefix << 27)
        | (cls << 23)
        | (op << 17)
        | (rd << 12)
        | (rs1 << 7)
        | (rs2 << 2)
        | fmt
    ) & MASK32


def decode_extended_header(w):
    """Decode the fixed 27-bit header of an extended instruction word."""
    w &= MASK32
    cls = (w >> 23) & 0xF
    op = (w >> 17) & 0x3F
    rd = (w >> 12) & 0x1F
    rs1 = (w >> 7) & 0x1F
    rs2 = (w >> 2) & 0x1F
    fmt = w & 0x3
    validate_extended_header(cls, op, rd, rs1, rs2, fmt)
    return (cls, op, rd, rs1, rs2, fmt)


def decode_stream(data):
    """Decode instruction boundaries without interpreting extended payloads."""
    if len(data) % 4:
        raise ValueError("instruction stream must be word aligned")
    out = []
    pc = 0
    while pc < len(data):
        if len(data) - pc < 4:
            raise IllegalEncoding("truncated instruction")
        w = from_bytes(data[pc:pc+4])
        n = instruction_length(w)
        if len(data) - pc < n:
            raise IllegalEncoding("truncated extended instruction")
        if n == 4:
            decoded = decode(w)
            out.append((pc, n, decoded))
        else:
            header = decode_extended_header(w)
            payload = data[pc+4:pc+n]
            out.append((pc, n, header, payload))
        pc += n
    return out


# Compatibility aliases used by the early reference tests/tooling.
def encode_base_r(name, rd, rs1, rs2):
    if name not in ALUR.values():
        raise IllegalEncoding("unknown ALUR operation")
    funct = next(k for k, v in ALUR.items() if v == name)
    return encode_r(funct, rd, rs1, rs2)

def encode_base_i(name, rd, rs1, imm):
    if name not in ALUI.values():
        raise IllegalEncoding("unknown ALUI operation")
    funct = next(k for k, v in ALUI.items() if v == name)
    return encode_i(funct, rd, rs1, imm)


from dataclasses import dataclass

EXTENDED_CLASSES = {0: 'SCALAR', 1: 'MEMORY', 2: 'FP', 3: 'VECTOR', 4: 'MATRIX', 5: 'SYSTEM', 6: 'VM', 7: 'CRYPTO', 8: 'DEVICE'}
EXTENDED_FORMATS = {0: 'IMMEDIATE_CONTROL', 1: 'REGISTER_OPERAND', 2: 'VECTOR_MATRIX_DESCRIPTOR', 3: 'CLASS_DEFINED'}

def validate_extended_header(cls, op=0, rd=0, rs1=0, rs2=0, fmt=0):
    if cls not in EXTENDED_CLASSES:
        raise IllegalEncoding('reserved extended class')
    if not 0 <= op <= 0x3F:
        raise IllegalEncoding('extended operation out of range')
    for name, value in (('rd', rd), ('rs1', rs1), ('rs2', rs2)):
        if not 0 <= value <= 0x1F:
            raise IllegalEncoding(name + ' register out of range')
    if fmt not in EXTENDED_FORMATS:
        raise IllegalEncoding('extended format out of range')

def extended_payload_size(length):
    if length not in (8, 16):
        raise IllegalEncoding('invalid extended instruction length')
    return length - 4

@dataclass(frozen=True)
class ExtendedInstruction:
    """Canonical structural record for one extended instruction."""
    length: int
    cls: int
    op: int
    rd: int
    rs1: int
    rs2: int
    fmt: int
    payload: bytes

    def __post_init__(self):
        validate_extended_header(self.cls, self.op, self.rd, self.rs1, self.rs2, self.fmt)
        if len(self.payload) != extended_payload_size(self.length):
            raise IllegalEncoding('extended payload length does not match instruction length')

    def encode(self):
        header = encode_extended_header(
            self.cls, self.op, self.rd, self.rs1, self.rs2, self.fmt,
            length=self.length,
        )
        return header.to_bytes(4, "little") + self.payload


def encode_extended_instruction(cls, op=0, rd=0, rs1=0, rs2=0, fmt=0,
                                payload=b"", *, length=16):
    """Encode a complete 64-bit or 128-bit architectural instruction."""
    expected = extended_payload_size(length)
    payload = bytes(payload)
    if len(payload) != expected:
        raise IllegalEncoding("extended payload length does not match instruction length")
    return ExtendedInstruction(length, cls, op, rd, rs1, rs2, fmt, payload).encode()


def decode_extended_instruction(data):
    """Decode one complete extended instruction into its canonical record."""
    if len(data) < 4:
        raise IllegalEncoding("truncated extended instruction header")
    word = from_bytes(data[:4])
    length = instruction_length(word)
    if length == 4:
        raise IllegalEncoding("base instruction is not an extended instruction")
    if len(data) != length:
        raise IllegalEncoding("extended instruction length mismatch")
    cls, op, rd, rs1, rs2, fmt = decode_extended_header(word)
    return ExtendedInstruction(length, cls, op, rd, rs1, rs2, fmt, bytes(data[4:]))


def decode_instruction(data):
    """Decode one complete architectural instruction record."""
    if len(data) < 4:
        raise IllegalEncoding("truncated instruction")
    first = from_bytes(data[:4])
    length = instruction_length(first)
    if len(data) != length:
        raise IllegalEncoding("instruction length mismatch")
    if length == 4:
        return decode(first)
    return decode_extended_instruction(data)
