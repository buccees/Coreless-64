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
    return ((OP_ALUR<<27)|(rd<<22)|(rs1<<17)|(rs2<<12)|f)&MASK32

def encode_i(f,rd,rs1,imm):
    if not -(1<<11)<=imm<(1<<11):
        raise ValueError('imm12 out of range')
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
        return (['ST8','ST16','ST32','ST64'][width],rs2,rs1,sext(w&0x3fff,14))
    if op==OP_BRANCH:
        f=(w>>12)&31
        if f not in BRANCH:
            raise IllegalEncoding('bad branch')
        return (BRANCH[f],rs1,rs2,sext(w&0xfff,12))
    if op==OP_JUMP:
        f=(w>>12)&31
        if f not in JUMP:
            raise IllegalEncoding('bad jump')
        if f in (0,1,4) and rs1!=0:
            raise IllegalEncoding('reserved jump field')
        if f==4 and (rd!=0 or (w&0xfff)!=0):
            raise IllegalEncoding('bad RET')
        return (JUMP[f],rd,rs1,sext(w&0xfff,12))
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



def decode_extended_header(w):
    """Decode the fixed 27-bit header of an extended instruction word."""
    w &= MASK32
    cls = (w >> 23) & 0xF
    op = (w >> 17) & 0x3F
    rd = (w >> 12) & 0x1F
    rs1 = (w >> 7) & 0x1F
    rs2 = (w >> 2) & 0x1F
    fmt = w & 0x3
    if cls > 0x8:
        raise IllegalEncoding("reserved extended class")
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
