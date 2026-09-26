"""Minimal Coreless-64 architectural reference machine.

This is a deterministic conformance-oriented execution model, not a
performance emulator. It models architectural state and precise retirement.
"""

MASK64 = (1 << 64) - 1
class CorelessTrap(Exception):
    def __init__(self, cause, pc, tval=0):
        super().__init__(cause)
        self.cause, self.pc, self.tval = cause, pc, tval

class CorelessCPU:
    def __init__(self, memory_size=65536):
        self.r = [0] * 32
        self.pc = 0
        self.sp = 0
        self.memory = bytearray(memory_size)
        self.privilege = 3  # Machine
        self.halted = False
        self.cycle = 0
        self.instret = 0
        self.csrs = {i: 0 for i in range(0x20)}
        self.csrs[0x01] = 0  # IE
        self.csrs[0x0A] = 0  # CPU_ID
        self.csrs[0x0B] = 1  # CPU_COUNT

    def read_reg(self, n):
        return 0 if n == 0 else self.r[n]

    def write_reg(self, n, value):
        if n != 0:
            self.r[n] = value & MASK64

    def load_u(self, addr, size):
        if addr < 0 or addr + size > len(self.memory):
            raise CorelessTrap("data_access_fault", self.pc, addr)
        return int.from_bytes(self.memory[addr:addr+size], "little")

    def store_u(self, addr, size, value):
        if addr < 0 or addr + size > len(self.memory):
            raise CorelessTrap("data_access_fault", self.pc, addr)
        self.memory[addr:addr+size] = (value & ((1 << (size*8))-1)).to_bytes(size, "little")

    def step(self):
        if self.halted:
            return False
        from encoding import from_bytes, instruction_length, decode
        try:
            first = from_bytes(self.memory[self.pc:self.pc+4])
            length = instruction_length(first)
            if length != 4:
                raise CorelessTrap("extended_execution_not_implemented", self.pc)
            ins = decode(first)
            next_pc = (self.pc + 4) & MASK64
            name = ins[0]

            if name in ("ADD","SUB","MUL","AND","OR","XOR","SHL","SHR","SAR","ROL","ROR","SLT","SLTU","SEQ","SNE"):
                _, rd, a, b = ins
                x, y = self.read_reg(a), self.read_reg(b)
                if name=="ADD": z=x+y
                elif name=="SUB": z=x-y
                elif name=="MUL": z=x*y
                elif name=="AND": z=x&y
                elif name=="OR": z=x|y
                elif name=="XOR": z=x^y
                elif name=="SHL": z=x<<(y&63)
                elif name=="SHR": z=x>>(y&63)
                elif name=="SAR":
                    sx=x-(1<<64) if x&(1<<63) else x; z=sx>>(y&63)
                elif name=="ROL": s=y&63; z=x if s==0 else (x<<s)|(x>>(64-s))
                elif name=="ROR": s=y&63; z=x if s==0 else (x>>s)|(x<<(64-s))
                elif name=="SLT": z=int((x-(1<<64) if x&(1<<63) else x) < (y-(1<<64) if y&(1<<63) else y))
                elif name=="SLTU": z=int(x<y)
                elif name=="SEQ": z=int(x==y)
                else: z=int(x!=y)
                self.write_reg(rd,z)
            elif name=="NOT":
                self.write_reg(ins[1], ~self.read_reg(ins[2]))
            elif name=="NEG":
                self.write_reg(ins[1], -self.read_reg(ins[2]))
            elif name in ("ADDI","SUBI","ANDI","ORI","XORI"):
                _, rd, a, imm = ins; x=self.read_reg(a)
                z={"ADDI":x+imm,"SUBI":x-imm,"ANDI":x&imm,"ORI":x|imm,"XORI":x^imm}[name]
                self.write_reg(rd,z)
            elif name.startswith("LD"):
                _, rd, base, imm = ins
                width={"LD8":1,"LD16":2,"LD32":4,"LD64":8,"LD8U":1,"LD16U":2,"LD32U":4}[name]
                v=self.load_u((self.read_reg(base)+imm)&MASK64,width)
                if name in ("LD8","LD16","LD32"):
                    bits=width*8; v=v-(1<<bits) if v&(1<<(bits-1)) else v
                self.write_reg(rd,v)
            elif name.startswith("ST"):
                _, src, base, imm = ins
                width={"ST8":1,"ST16":2,"ST32":4,"ST64":8}[name]
                self.store_u((self.read_reg(base)+imm)&MASK64,width,self.read_reg(src))
            elif name in ("BEQ","BNE","BLT","BGE","BLTU","BGEU"):
                _, a, b, off = ins; x=self.read_reg(a); y=self.read_reg(b)
                sx=lambda v: v-(1<<64) if v&(1<<63) else v
                take={"BEQ":x==y,"BNE":x!=y,"BLT":sx(x)<sx(y),"BGE":sx(x)>=sx(y),"BLTU":x<y,"BGEU":x>=y}[name]
                if take: next_pc=(self.pc+off)&MASK64
            elif name in ("J","CALL","JR","CALLR","RET"):
                if name in ("J","CALL"): target=(self.pc+ins[2])&MASK64
                elif name in ("JR","CALLR"): target=(self.read_reg(ins[2])+ins[3])&MASK64
                else: target=self.read_reg(1)
                if name in ("CALL","CALLR"): self.write_reg(ins[1],self.pc+4)
                next_pc=target
            elif name=="NOP": pass
            elif name=="HALT": self.halted=True
            elif name=="WAIT": pass
            elif name in ("TRAP","RETX","FENCE","TLBFLUSH","TLBFLUSHVA","READCSR","WRITECSR"):
                raise CorelessTrap("system_execution_not_implemented", self.pc)
            else:
                raise CorelessTrap("illegal_instruction", self.pc)
            self.r[0]=0
            self.pc=next_pc
            self.cycle+=1
            self.instret+=1
            return True
        except CorelessTrap:
            raise
