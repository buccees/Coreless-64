"""Coreless-64 deterministic architectural reference machine.

This model is intentionally hardware-shaped: architectural state is explicit,
instruction retirement is precise, and translation/privilege/trap behavior is
kept separate from the host implementation.
"""

MASK64 = (1 << 64) - 1

# Architectural privilege domains.
USER, SUPERVISOR, HYPERVISOR, MACHINE = 0, 1, 2, 3

# CAUSE low-field synchronous exception codes.
CAUSE = {
    "instruction_access_fault": 0x000,
    "instruction_page_fault": 0x001,
    "illegal_instruction": 0x002,
    "illegal_csr": 0x003,
    "privilege_violation": 0x004,
    "breakpoint": 0x005,
    "alignment_fault": 0x006,
    "data_access_fault": 0x007,
    "data_page_fault": 0x008,
    "execute_permission_fault": 0x009,
    "write_permission_fault": 0x00A,
    "read_permission_fault": 0x00B,
    "malformed_translation": 0x00C,
    "invalid_memory_attribute": 0x00D,
    "arithmetic_fault": 0x00E,
    "floating_point_fault": 0x00F,
    "vector_fault": 0x010,
    "matrix_ai_fault": 0x011,
    "virtualization_fault": 0x012,
    "second_stage_translation_fault": 0x013,
    "capability_resource_fault": 0x014,
    "device_fault": 0x015,
    "machine_check_fault": 0x016,
    "instruction_encoding_fault": 0x017,
}

CSR_ACCESS = {
    0x000: ("STATUS", "rw", MACHINE),
    0x001: ("IE", "rw", MACHINE),
    0x002: ("IP", "rw", MACHINE),
    0x003: ("TVEC", "rw", MACHINE),
    0x004: ("EPC", "rw", MACHINE),
    0x005: ("CAUSE", "r", MACHINE),
    0x006: ("TVAL", "rw", MACHINE),
    0x007: ("ROOT", "rw", MACHINE),
    0x008: ("ASID", "rw", SUPERVISOR),
    0x009: ("TLBCTL", "rw", MACHINE),
    0x00A: ("CPU_ID", "r", USER),
    0x00B: ("CPU_COUNT", "r", USER),
    0x00C: ("CAP_BASE", "r", USER),
    0x00D: ("TIME", "r", USER),
    0x00E: ("CYCLE", "r", USER),
    0x00F: ("INSTRET", "r", USER),
    0x010: ("FSTATUS", "rw", USER),
    0x011: ("VSTART", "rw", USER),
    0x012: ("VL", "rw", USER),
    0x013: ("VTYPE", "rw", USER),
    0x014: ("VCSR", "rw", USER),
    0x015: ("MSTATUS", "rw", SUPERVISOR),
    0x016: ("VMSPEC", "r", HYPERVISOR),
    0x017: ("VROOT", "rw", HYPERVISOR),
    0x018: ("VMID", "rw", HYPERVISOR),
    0x019: ("VMCTL", "rw", HYPERVISOR),
    0x01A: ("IBASE", "rw", SUPERVISOR),
    0x01B: ("IPRIO", "rw", SUPERVISOR),
    0x01C: ("FENCECTL", "rw", MACHINE),
    0x01D: ("BOOT_STATUS", "r", MACHINE),
    0x01E: ("MACHINE_CFG", "rw", MACHINE),
    0x01F: ("ARCH_ID", "r", USER),
}


class CorelessTrap(Exception):
    def __init__(self, cause, pc, tval=0):
        super().__init__(cause)
        self.cause, self.pc, self.tval = cause, pc, tval


class CorelessCPU:
    """Small deterministic reference machine.

    Physical memory is backed by a bytearray.  When TLBCTL bit 0 is set,
    accesses use the baseline 4 KiB page-table format.  This bit is a
    reference-model control convention; the architectural CSR semantics
    remain defined by the specification.
    """

    def __init__(self, memory_size=65536):
        self.r = [0] * 32
        self.pc = 0
        self.sp = 0
        self.memory = bytearray(memory_size)
        self.privilege = MACHINE
        self.halted = False
        self.cycle = 0
        self.instret = 0
        self.csrs = {i: 0 for i in range(0x20)}
        self.csrs[0x00A] = 0
        self.csrs[0x00B] = 1
        self.csrs[0x00C] = 0
        self.csrs[0x01D] = 0
        self.csrs[0x01F] = 0x434C3634  # "CL64"
        self.tlb = {}
        self.pending_interrupts = 0
        self.reservation = None
        self.vector = [[0] * 64 for _ in range(32)]
        self.matrix = [[[0] * 16 for _ in range(16)] for _ in range(32)]
        self.vector_vl = 0
        self.vector_vstart = 0
        self.vector_vtype = 0
        self.vector_mask = [0] * 32
        self.matrix_shape = (1, 1, 1)
        self._trap_saved_privilege = MACHINE
        self._trap_saved_ie = 0

    def read_reg(self, n):
        return 0 if n == 0 else self.r[n]

    def write_reg(self, n, value):
        if n != 0:
            self.r[n] = value & MASK64

    def _csr_info(self, csr):
        return CSR_ACCESS.get(csr)

    def read_csr(self, csr):
        info = self._csr_info(csr)
        if info is None or self.privilege < info[2]:
            raise CorelessTrap("illegal_csr" if info is None else "privilege_violation", self.pc, csr)
        if csr == 0x00D:
            return self.cycle & MASK64
        if csr == 0x00E:
            return self.cycle & MASK64
        if csr == 0x00F:
            return self.instret & MASK64
        if csr == 0x000:
            return self.privilege & 0x3
        if csr == 0x002:
            return self.pending_interrupts & MASK64
        return self.csrs[csr] & MASK64

    def write_csr(self, csr, value):
        info = self._csr_info(csr)
        if info is None:
            raise CorelessTrap("illegal_csr", self.pc, csr)
        _, access, required = info
        if self.privilege < required or access != "rw":
            raise CorelessTrap("privilege_violation" if self.privilege < required else "illegal_csr",
                               self.pc, csr)
        value &= MASK64
        if csr == 0x000:
            self.privilege = value & 0x3
            self.csrs[csr] = self.privilege
        elif csr == 0x002:
            self.pending_interrupts = value
            self.csrs[csr] = value
        else:
            self.csrs[csr] = value
        if csr == 0x007:
            self.tlb.clear()

    def _phys(self, addr, access="read", execute=False):
        addr &= MASK64
        enabled = bool(self.csrs[0x009] & 1)
        if not enabled:
            return addr

        vpn = addr >> 12
        page_off = addr & 0xFFF
        pte_addr = (self.csrs[0x007] & MASK64) + vpn * 8
        if pte_addr & 7:
            raise CorelessTrap("malformed_translation", self.pc, addr)
        if vpn in self.tlb:
            pte = self.tlb[vpn]
        else:
            if pte_addr + 8 > len(self.memory):
                raise CorelessTrap("data_page_fault", self.pc, addr)
            pte = int.from_bytes(self.memory[pte_addr:pte_addr+8], "little")
            valid = pte & 1
            if not valid:
                raise CorelessTrap("instruction_page_fault" if execute else "data_page_fault", self.pc, addr)
            if (pte >> 11) & 1:
                raise CorelessTrap("malformed_translation", self.pc, addr)
            memtype = (pte >> 8) & 3
            if memtype == 3:
                raise CorelessTrap("invalid_memory_attribute", self.pc, addr)
            if pte & (1 << 2) and not (pte & (1 << 1)):
                # Write-only mappings are capability-dependent and are not
                # advertised by this baseline reference machine.
                raise CorelessTrap("malformed_translation", self.pc, addr)
            ppn = (pte >> 12) & ((1 << 36) - 1)
            self.tlb[vpn] = pte
        user = bool(pte & (1 << 4))
        if self.privilege == USER and not user:
            raise CorelessTrap("data_page_fault" if not execute else "instruction_page_fault", self.pc, addr)
        if execute and not (pte & (1 << 3)):
            raise CorelessTrap("execute_permission_fault", self.pc, addr)
        if access == "write" and not (pte & (1 << 2)):
            raise CorelessTrap("write_permission_fault", self.pc, addr)
        if access == "read" and not (pte & (1 << 1)):
            raise CorelessTrap("read_permission_fault", self.pc, addr)
        if pte & (1 << 6) == 0:
            pte |= 1 << 6
        if access == "write" and pte & (1 << 7) == 0:
            pte |= 1 << 7
        self.tlb[vpn] = pte
        self.memory[pte_addr:pte_addr+8] = pte.to_bytes(8, "little")
        return ((ppn << 12) | page_off) & MASK64

    def load_u(self, addr, size, execute=False):
        if size not in (1, 2, 4, 8):
            raise CorelessTrap("data_access_fault", self.pc, addr)
        if addr & (size - 1):
            raise CorelessTrap("alignment_fault", self.pc, addr)
        phys = self._phys(addr, "read", execute)
        if phys + size > len(self.memory):
            raise CorelessTrap("instruction_access_fault" if execute else "data_access_fault", self.pc, addr)
        return int.from_bytes(self.memory[phys:phys+size], "little")

    def store_u(self, addr, size, value):
        if size not in (1, 2, 4, 8):
            raise CorelessTrap("data_access_fault", self.pc, addr)
        if addr & (size - 1):
            raise CorelessTrap("alignment_fault", self.pc, addr)
        phys = self._phys(addr, "write")
        if phys + size > len(self.memory):
            raise CorelessTrap("data_access_fault", self.pc, addr)
        self.memory[phys:phys+size] = (value & ((1 << (size*8))-1)).to_bytes(size, "little")

    def _enter_trap(self, trap):
        cause_code = CAUSE.get(trap.cause, 0x017)
        self._trap_saved_privilege = self.privilege
        self._trap_saved_ie = self.csrs[0x001]
        self.csrs[0x004] = trap.pc & MASK64
        self.csrs[0x005] = ((self.privilege & 0x7F) << 56) | cause_code
        self.csrs[0x006] = trap.tval & MASK64
        self.csrs[0x001] = 0
        self.privilege = max(self.privilege, SUPERVISOR)
        self.csrs[0x000] = self.privilege
        self.pc = self.csrs[0x003] & MASK64

    def request_interrupt(self, code):
        self.pending_interrupts |= 1 << code
        self.csrs[0x002] = self.pending_interrupts

    def _take_interrupt_if_enabled(self):
        enabled = self.csrs[0x001]
        pending = self.pending_interrupts & enabled
        if not pending:
            return False
        bit = (pending & -pending).bit_length() - 1
        self.pending_interrupts &= ~(1 << bit)
        self.csrs[0x002] = self.pending_interrupts
        self._trap_saved_privilege = self.privilege
        self._trap_saved_ie = self.csrs[0x001]
        self.csrs[0x004] = self.pc
        self.csrs[0x005] = (1 << 63) | ((self.privilege & 0x7F) << 56) | bit
        self.csrs[0x001] = 0
        self.privilege = max(self.privilege, SUPERVISOR)
        self.csrs[0x000] = self.privilege
        self.pc = self.csrs[0x003] & MASK64
        return True



    def _vector_op(self, cls, op, rd, rs1, rs2, w1):
        et = (w1 >> 29) & 7
        if et > 7: raise CorelessTrap("vector_fault", self.pc, et)
        bits = (8,16,32,64,16,16,32,64)[et]
        vl = self.vector_vl or 1
        if vl > len(self.vector[rd]): raise CorelessTrap("capability_resource_fault", self.pc, vl)
        start = min(self.vector_vstart, vl)
        mode = (w1 >> 27) & 3
        mask_en = bool((w1 >> 22) & 1)
        mask_zero = bool((w1 >> 21) & 1)
        vs3 = (w1 >> 16) & 0x1F
        mask = self.vector_mask[vs3]
        mod = 1 << bits
        def sextv(x):
            x &= mod-1
            return x-(1<<bits) if x & (1<<(bits-1)) else x
        for i in range(start, vl):
            active = (not mask_en) or bool((mask >> i) & 1)
            if not active:
                if mask_zero: self.vector[rd][i] = 0
                continue
            a, b = self.vector[rs1][i] & (mod-1), self.vector[rs2][i] & (mod-1)
            if op == 0x00: z = a + b
            elif op == 0x01: z = a - b
            elif op == 0x02: z = a * b
            elif op == 0x04: z = min(sextv(a), sextv(b))
            elif op == 0x05: z = max(sextv(a), sextv(b))
            elif op == 0x06: z = a & b
            elif op == 0x07: z = a | b
            elif op == 0x08: z = a ^ b
            elif op == 0x09: z = ~a
            elif op == 0x0A: z = a << (b & (bits-1))
            elif op == 0x0B: z = a >> (b & (bits-1))
            elif op == 0x0C: z = sextv(a) >> (b & (bits-1))
            elif op == 0x0D: s=b & (bits-1); z=a if s==0 else (a<<s)|(a>>(bits-s))
            elif op == 0x0E: s=b & (bits-1); z=a if s==0 else (a>>s)|(a<<(bits-s))
            elif op == 0x15: z = -sextv(a)
            elif op == 0x16: z = abs(sextv(a))
            elif op == 0x1E:
                z = a
            elif op == 0x1F:
                self.vector[rd][i] = a
                continue
            else:
                raise CorelessTrap("vector_fault", self.pc, op)
            self.vector[rd][i] = z & (mod-1)
        self.vector_vstart = 0
        return

    def _matrix_op(self, op, rd, rs1, rs2, w1, w2, w3):
        it = (w1 >> 29) & 7
        at = (w1 >> 26) & 7
        shape = (w1 >> 23) & 7
        shapes = ((2,2,2),(4,4,4),(8,8,8),(8,16,16),(16,8,16),(16,16,16),(32,8,16))
        if shape >= len(shapes): raise CorelessTrap("matrix_ai_fault", self.pc, shape)
        m,n,k = shapes[shape]
        if m > 16 or n > 16 or k > 16: raise CorelessTrap("capability_resource_fault", self.pc, shape)
        mask = 1 << 63
        if op in (0x00,0x01,0x02,0x03,0x06):
            for i in range(m):
                for j in range(n):
                    acc = self.matrix[rd][i][j] if op in (0x01,0x06) else 0
                    for q in range(k):
                        acc += self.matrix[rs1][i][q] * self.matrix[rs2][q][j]
                    self.matrix[rd][i][j] = acc
        elif op == 0x04:
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = self.matrix[rs1][i][j] + self.matrix[rs2][i][j]
        elif op == 0x05:
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = self.matrix[rs1][i][j] - self.matrix[rs2][i][j]
        elif op == 0x07:
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = self.matrix[rs1][j][i]
        elif op == 0x08:
            self.matrix[rd] = [[self.matrix[rs1][i][j] for j in range(n)] for i in range(m)]
        elif op == 0x0B:
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = 0
        elif op == 0x0C:
            value = self.read_reg(rs1)
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = value
        elif op == 0x0D:
            total = 0
            for i in range(m):
                for j in range(n): total += self.matrix[rs1][i][j]
            self.write_reg(rd, total)
        elif op == 0x0E:
            lo, hi = -(1<<31), (1<<31)-1
            for i in range(m):
                for j in range(n): self.matrix[rd][i][j] = max(lo, min(hi, self.matrix[rs1][i][j]))
        else:
            raise CorelessTrap("matrix_ai_fault", self.pc, op)
        return

    def _atomic(self, ins):
        """Execute the compact architectural ATOMIC R-format subset."""
        _, rd, addr_reg, src = ins
        raw = self._last_word
        funct = raw & 0xF
        desired_reg = (raw >> 4) & 0x1F
        ordering = (raw >> 9) & 0x7
        addr = self.read_reg(addr_reg)
        old = self.load_u(addr, 8)
        if funct == 0: new = self.read_reg(src)
        elif funct == 1:
            if old == self.read_reg(src):
                new = self.read_reg(desired_reg)
            else:
                new = old
        elif funct == 2: new = (old + self.read_reg(src)) & MASK64
        elif funct == 3: new = (old - self.read_reg(src)) & MASK64
        elif funct == 4: new = old & self.read_reg(src)
        elif funct == 5: new = old | self.read_reg(src)
        elif funct == 6: new = old ^ self.read_reg(src)
        elif funct == 7:
            a = old - (1<<64) if old & (1<<63) else old
            b0 = self.read_reg(src); b = b0 - (1<<64) if b0 & (1<<63) else b0
            new = old if a < b else b0
        elif funct == 8:
            a = old - (1<<64) if old & (1<<63) else old
            b0 = self.read_reg(src); b = b0 - (1<<64) if b0 & (1<<63) else b0
            new = old if a > b else b0
        elif funct == 9:
            new = old
            self.write_reg(rd, old)
            return
        elif funct == 10:
            self.store_u(addr, 8, self.read_reg(src))
            return
        else:
            raise CorelessTrap("illegal_instruction", self.pc, funct)
        if funct != 1 or old == self.read_reg(src):
            self.store_u(addr, 8, new)
        self.write_reg(rd, old)
        self.reservation = (addr >> 3, old, ordering)

    def _execute(self, ins):
        from encoding import instruction_length
        name = ins[0]
        next_pc = (self.pc + 4) & MASK64

        if name in ("ADD","SUB","MUL","DIV","UDIV","REM","UREM","AND","OR","XOR","SHL","SHR","SAR","ROL","ROR","SLT","SLTU","SEQ","SNE"):
            _, rd, a, b = ins
            x, y = self.read_reg(a), self.read_reg(b)
            sx = lambda v: v - (1 << 64) if v & (1 << 63) else v
            if name=="ADD": z=x+y
            elif name=="SUB": z=x-y
            elif name=="MUL": z=x*y
            elif name=="DIV":
                if y == 0: raise CorelessTrap("arithmetic_fault", self.pc, 0)
                if x == (1<<63) and y == MASK64:
                    z = 1 << 63
                else:
                    ax, ay = sx(x), sx(y)
                    z = (abs(ax) // abs(ay)) * (-1 if (ax < 0) != (ay < 0) else 1)
            elif name=="UDIV":
                if y == 0: raise CorelessTrap("arithmetic_fault", self.pc, 0)
                z=x//y
            elif name=="REM":
                if y == 0: raise CorelessTrap("arithmetic_fault", self.pc, 0)
                if x == (1<<63) and y == MASK64:
                    z = 0
                else:
                    ax, ay = sx(x), sx(y)
                    z = ax - (abs(ax) // abs(ay)) * ay
            elif name=="UREM":
                if y == 0: raise CorelessTrap("arithmetic_fault", self.pc, 0)
                z=x%y
            elif name=="AND": z=x&y
            elif name=="OR": z=x|y
            elif name=="XOR": z=x^y
            elif name=="SHL": z=x<<(y&63)
            elif name=="SHR": z=x>>(y&63)
            elif name=="SAR": z=sx(x)>>(y&63)
            elif name=="ROL": s=y&63; z=x if s==0 else (x<<s)|(x>>(64-s))
            elif name=="ROR": s=y&63; z=x if s==0 else (x>>s)|(x<<(64-s))
            elif name=="SLT": z=int(sx(x)<sx(y))
            elif name=="SLTU": z=int(x<y)
            elif name=="SEQ": z=int(x==y)
            else: z=int(x!=y)
            self.write_reg(rd,z)
        elif name=="NOT": self.write_reg(ins[1],~self.read_reg(ins[2]))
        elif name=="NEG": self.write_reg(ins[1],-self.read_reg(ins[2]))
        elif name in ("ADDI","SUBI","ANDI","ORI","XORI"):
            _, rd, a, imm = ins
            x=self.read_reg(a)
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
        elif name=="ATOMIC": self._atomic(ins)
        elif name=="HALT":
            self.halted=True
        elif name=="WAIT":
            if not (self.pending_interrupts & self.csrs[0x001]):
                return "wait"
        elif name=="TRAP":
            self._enter_trap(CorelessTrap("breakpoint", self.pc, ins[3]))
            return "trap"
        elif name=="RETX":
            if self.privilege < SUPERVISOR:
                raise CorelessTrap("privilege_violation", self.pc, 0)
            self.privilege = self._trap_saved_privilege
            self.csrs[0x000] = self.privilege
            self.csrs[0x001] = self._trap_saved_ie
            next_pc = self.csrs[0x004] & MASK64
        elif name=="FENCE":
            # Architectural ordering point; concrete cache machinery is
            # implementation-defined in the reference machine.
            pass
        elif name=="TLBFLUSH":
            self.tlb.clear()
        elif name=="TLBFLUSHVA":
            self.tlb.pop(self.read_reg(ins[1]) >> 12, None)
        elif name=="READCSR":
            self.write_reg(ins[1], self.read_csr(ins[3] & 0xFFFF))
        elif name=="WRITECSR":
            self.write_csr(ins[3] & 0xFFFF, self.read_reg(ins[1]))
        else:
            raise CorelessTrap("illegal_instruction", self.pc)
        return next_pc

    def step(self):
        if self.halted:
            return False
        if self._take_interrupt_if_enabled():
            return True
        from encoding import from_bytes, instruction_length, decode, IllegalEncoding
        try:
            first = from_bytes(self.memory[self._phys(self.pc, "read", execute=True):
                                           self._phys(self.pc, "read", execute=True)+4])
            self._last_word = first
            length = instruction_length(first)
            if length == 16:
                from encoding import decode_extended_header
                h = decode_extended_header(first)
                words = [int.from_bytes(self.memory[self._phys(self.pc+i, "read", execute=True):self._phys(self.pc+i, "read", execute=True)+4], "little") for i in (4,8,12)]
                cls, op, rd, rs1, rs2, fmt = h
                if fmt != 2: raise CorelessTrap("instruction_encoding_fault", self.pc, fmt)
                if cls == 3:
                    self._vector_op(cls, op, rd, rs1, rs2, words[0])
                elif cls == 4:
                    self._matrix_op(op, rd, rs1, rs2, words[0], words[1], words[2])
                else:
                    raise CorelessTrap("illegal_instruction", self.pc, cls)
                next_pc = (self.pc + 16) & MASK64
            else:
                ins = decode(first)
                next_pc = self._execute(ins)
            if next_pc == "wait" or next_pc == "trap":
                self.r[0] = 0
                return True
            if next_pc & 3:
                raise CorelessTrap("alignment_fault", self.pc, next_pc)
            self.r[0] = 0
            self.pc = next_pc & MASK64
            self.cycle += 1
            self.instret += 1
            return True
        except IllegalEncoding:
            trap = CorelessTrap("illegal_instruction", self.pc, 0)
            self._enter_trap(trap)
            return True
        except CorelessTrap as trap:
            self._enter_trap(trap)
            return True
