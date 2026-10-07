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
    "syscall": 0x019,
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

    def __init__(self, memory_size=65536, storage=None, memory_name="ram0", memory=None):
        self.r = [0] * 32
        self.f = [0] * 32
        self.fp_rounding = 0
        self.pc = 0
        self.sp = 0
        from memory import VirtualRAM
        self.memory = memory if memory is not None else VirtualRAM(memory_size, storage, memory_name)
        if len(self.memory) != memory_size:
            raise ValueError("Coreless CPU memory size does not match shared RAM")
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
        self.syscall_handler = None  # legacy compatibility; SYSCALL no longer bypasses traps
        self.supervisor_trap_handler = None
        self.vm_handler = None
        self._last_step_event = None
        self._last_step_result = {"event": "reset", "pc": self.pc, "cause": None, "tval": 0}

    def reset(self):
        """Return architectural state to the defined power-on reset state.

        Reset preserves the backing memory contents; it resets the CPU's
        architectural execution state, privilege state, counters, translation
        state, interrupt state, vector/matrix state, and trap context.
        """
        memory = self.memory
        memory_size = len(memory)
        self.__init__(memory_size=memory_size, memory=memory)

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
        if csr == 0x010:
            return self.csrs[csr] & MASK64
        if csr == 0x011:
            return self.vector_vstart & MASK64
        if csr == 0x012:
            return self.vector_vl & MASK64
        if csr == 0x013:
            return self.vector_vtype & MASK64
        if csr == 0x014:
            return self.csrs[csr] & MASK64
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
        elif csr == 0x010:
            if value & ~0x7:
                raise CorelessTrap("illegal_instruction", self.pc, value)
            self.fp_rounding = value & 0x7
            self.csrs[csr] = value & 0x7
        elif csr == 0x011:
            self.vector_vstart = value
            self.csrs[csr] = value
        elif csr == 0x012:
            if value > len(self.vector[0]):
                raise CorelessTrap("capability_resource_fault", self.pc, value)
            self.vector_vl = value
            self.csrs[csr] = value
        elif csr == 0x013:
            self.vector_vtype = value
            self.csrs[csr] = value
        elif csr == 0x014:
            self.csrs[csr] = value
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
            ppn = (pte >> 12) & ((1 << 36) - 1)
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
        bits = (8, 16, 32, 64, 16, 16, 32, 64)[et]
        vl = self.vector_vl or 1
        if vl > len(self.vector[rd]):
            raise CorelessTrap("capability_resource_fault", self.pc, vl)
        start = min(self.vector_vstart, vl)
        mask_en = bool((w1 >> 22) & 1)
        mask_zero = bool((w1 >> 21) & 1)
        mask_reg = (w1 >> 16) & 0x1F
        mask = self.vector_mask[mask_reg]
        mod = 1 << bits

        import math, struct
        fp_type = et in (4, 5, 6, 7)
        if fp_type and ((w1 >> 8) & 0x7):
            raise CorelessTrap("illegal_instruction", self.pc, (w1 >> 8) & 0x7)

        def fp_decode(raw, typ):
            if typ == 4:
                return struct.unpack("<e", (raw & 0xFFFF).to_bytes(2, "little"))[0]
            if typ == 5:
                return struct.unpack("<f", ((raw & 0xFFFF) << 16).to_bytes(4, "little"))[0]
            if typ == 6:
                return struct.unpack("<f", (raw & 0xFFFFFFFF).to_bytes(4, "little"))[0]
            if typ == 7:
                return struct.unpack("<d", (raw & MASK64).to_bytes(8, "little"))[0]
            raise ValueError("not floating-point")

        def fp_encode(value, typ):
            if typ == 4:
                return int.from_bytes(struct.pack("<e", float(value)), "little")
            if typ == 5:
                raw = int.from_bytes(struct.pack("<f", float(value)), "little")
                low, high = raw & 0xFFFF, raw >> 16
                if low > 0x8000 or (low == 0x8000 and (high & 1)):
                    high = (high + 1) & 0xFFFF
                return high
            if typ == 6:
                return int.from_bytes(struct.pack("<f", float(value)), "little")
            if typ == 7:
                return int.from_bytes(struct.pack("<d", float(value)), "little")
            raise ValueError("not floating-point")

        def fp_minmax(a, b, is_min):
            if math.isnan(a): return b
            if math.isnan(b): return a
            if a == b == 0.0:
                return -0.0 if is_min else 0.0
            return min(a, b) if is_min else max(a, b)

        def sextv(x):
            x &= mod - 1
            return x - (1 << bits) if x & (1 << (bits - 1)) else x

        def active(i):
            return (not mask_en) or bool((mask >> i) & 1)

        if op in (0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D):
            if fp_type and op in (0x18, 0x19, 0x1A):
                values = [fp_decode(self.vector[rs1][i], et) for i in range(start, vl) if active(i)]
                if not values:
                    return
                result = values[0]
                for value in values[1:]:
                    if op == 0x18:
                        result = result + value
                    elif op == 0x19:
                        result = fp_minmax(result, value, True)
                    else:
                        result = fp_minmax(result, value, False)
                self.vector[rd][0] = fp_encode(result, et)
                self.vector_vstart = 0
                return
            values = []
            for i in range(start, vl):
                if active(i):
                    values.append(self.vector[rs1][i] & (mod - 1))
            if not values:
                return
            if op == 0x18:
                result = sum(values) & (mod - 1)
            elif op == 0x19:
                result = min(sextv(v) for v in values) & (mod - 1)
            elif op == 0x1A:
                result = max(sextv(v) for v in values) & (mod - 1)
            elif op == 0x1B:
                result = values[0]
                for v in values[1:]:
                    result &= v
            elif op == 0x1C:
                result = values[0]
                for v in values[1:]:
                    result |= v
            else:
                result = values[0]
                for v in values[1:]:
                    result ^= v
            self.write_reg(rd, result)
            self.vector_vstart = 0
            return

        if op in (0x12, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25):
            index = self.read_reg(rs2) & 0x3F
            if op == 0x12:
                # VSEL uses the selected architectural mask as the lane
                # selector: 1 selects vs1, 0 selects vs2.
                for i in range(start, vl):
                    if (mask >> i) & 1:
                        self.vector[rd][i] = self.vector[rs1][i] & (mod - 1)
                    else:
                        self.vector[rd][i] = self.vector[rs2][i] & (mod - 1)
                self.vector_vstart = 0
                return
            if op in (0x20, 0x21):
                # Indexed memory uses rs1 as the base and each active
                # element of rs2 as a byte offset. The current element
                # width determines the transfer size.
                width = max(1, bits // 8)
                for i in range(start, vl):
                    self.vector_vstart = i
                    if not active(i):
                        if mask_zero and op == 0x20:
                            self.vector[rd][i] = 0
                        continue
                    offset = self.vector[rs2][i] & MASK64
                    addr = (self.read_reg(rs1) + offset) & MASK64
                    if op == 0x20:
                        self.vector[rd][i] = self.load_u(addr, width) & (mod - 1)
                    else:
                        self.store_u(addr, width, self.vector[rd][i])
                self.vector_vstart = 0
                return
            if op == 0x22:
                for i in range(start, vl):
                    if not active(i):
                        if mask_zero:
                            self.vector[rd][i] = 0
                        continue
                    src = self.vector[rs2][i] & 0x3F
                    if src >= vl:
                        raise CorelessTrap("vector_fault", self.pc, src)
                    self.vector[rd][i] = self.vector[rs1][src] & (mod - 1)
                self.vector_vstart = 0
                return
            if op == 0x23:
                value = self.read_reg(rs1) & (mod - 1)
                for i in range(start, vl):
                    if active(i):
                        self.vector[rd][i] = value
            elif op == 0x24:
                if index >= vl:
                    raise CorelessTrap("vector_fault", self.pc, index)
                self.write_reg(rd, self.vector[rs1][index])
            else:
                if index >= vl:
                    raise CorelessTrap("vector_fault", self.pc, index)
                self.vector[rd][index] = self.read_reg(rs1) & (mod - 1)
            self.vector_vstart = 0
            return

        for i in range(start, vl):
            self.vector_vstart = i
            if not active(i):
                if mask_zero:
                    self.vector[rd][i] = 0
                continue
            a = self.vector[rs1][i] & (mod - 1)
            b = self.vector[rs2][i] & (mod - 1)
            if op == 0x17:
                src_et = (w1 >> 29) & 7
                dst_et = (w1 >> 11) & 7
                type_bits = (8, 16, 32, 64, 16, 16, 32, 64)
                src_bits, dst_bits = type_bits[src_et], type_bits[dst_et]
                src_mask = (1 << src_bits) - 1
                dst_mod = 1 << dst_bits
                raw_src = a & src_mask
                src_is_fp, dst_is_fp = src_et in (4,5,6,7), dst_et in (4,5,6,7)
                signed_src, saturate = bool(w1 & 1), bool(w1 & 2)
                if src_is_fp:
                    src_value = fp_decode(raw_src, src_et)
                else:
                    src_value = raw_src - (1 << src_bits) if signed_src and (raw_src & (1 << (src_bits - 1))) else raw_src
                if dst_is_fp:
                    z = fp_encode(src_value, dst_et)
                else:
                    if math.isnan(src_value) or math.isinf(src_value):
                        z = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                    else:
                        z = int(src_value)
                        lo = -(1 << (dst_bits - 1)) if signed_src else 0
                        hi = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                        if saturate:
                            z = min(max(z, lo), hi)
                    z &= dst_mod - 1
                self.vector[rd][i] = z
                continue
            if fp_type:
                fa, fb = fp_decode(a, et), fp_decode(b, et)
                fc = fp_decode(self.vector[rd][i], et)
                try:
                    if op == 0x00: fv = fa + fb
                    elif op == 0x01: fv = fa - fb
                    elif op == 0x02: fv = fa * fb
                    elif op == 0x03:
                        if fb == 0.0 and fa == 0.0: fv = float("nan")
                        elif fb == 0.0: fv = math.copysign(float("inf"), fa * fb)
                        else: fv = fa / fb
                    elif op == 0x04: fv = fp_minmax(fa, fb, True)
                    elif op == 0x05: fv = fp_minmax(fa, fb, False)
                    elif op == 0x0F: fv = int(not math.isnan(fa) and not math.isnan(fb) and fa == fb)
                    elif op == 0x10: fv = int(not math.isnan(fa) and not math.isnan(fb) and fa < fb)
                    elif op == 0x13: fv = fa * fb + fc
                    elif op == 0x14: fv = fc - fa * fb
                    elif op == 0x15: fv = -fa
                    elif op == 0x16: fv = abs(fa)
                    else: raise CorelessTrap("illegal_instruction", self.pc, op)
                    z = fv if isinstance(fv, int) else fp_encode(fv, et)
                except (OverflowError, struct.error):
                    z = fp_encode(math.copysign(float("inf"), fa), et)
                self.vector[rd][i] = z & (mod - 1)
                continue
            sa, sb = sextv(a), sextv(b)

            if op == 0x00: z = a + b
            elif op == 0x01: z = a - b
            elif op == 0x13: z = a * b + self.vector[rd][i]
            elif op == 0x14: z = self.vector[rd][i] - a * b
            elif op == 0x02: z = a * b
            elif op == 0x03:
                if b == 0:
                    raise CorelessTrap("arithmetic_fault", self.pc, i)
                z = (abs(sa) // abs(sb)) * (-1 if (sa < 0) != (sb < 0) else 1)
            elif op == 0x04: z = min(sa, sb)
            elif op == 0x05: z = max(sa, sb)
            elif op == 0x06: z = a & b
            elif op == 0x07: z = a | b
            elif op == 0x08: z = a ^ b
            elif op == 0x09: z = ~a
            elif op == 0x0A: z = a << (b & (bits - 1))
            elif op == 0x0B: z = a >> (b & (bits - 1))
            elif op == 0x0C: z = sa >> (b & (bits - 1))
            elif op == 0x0D:
                s = b & (bits - 1); z = a if s == 0 else (a << s) | (a >> (bits - s))
            elif op == 0x0E:
                s = b & (bits - 1); z = a if s == 0 else (a >> s) | (a << (bits - s))
            elif op == 0x0F: z = int(a == b)
            elif op == 0x10: z = int(sa < sb)
            elif op == 0x11: z = int(a < b)
            elif op == 0x15: z = -sa
            elif op == 0x16: z = abs(sa)
            elif op == 0x17:
                # Conversion descriptor: source type is w1[31:29],
                # destination type is w1[13:11]. Integer conversions use
                # sign-extension/truncation according to the source type.
                src_et = (w1 >> 29) & 7
                src_bits = (8, 16, 32, 64, 16, 16, 32, 64)[src_et]
                dst_et = (w1 >> 11) & 7
                dst_bits = (8, 16, 32, 64, 16, 16, 32, 64)[dst_et]
                dst_mod = 1 << dst_bits
                src_mask = (1 << src_bits) - 1
                raw_src = a & src_mask
                signed_src = bool(w1 & 0x1)
                saturate = bool(w1 & 0x2)
                src_is_fp = src_et in (4, 5, 6, 7)
                dst_is_fp = dst_et in (4, 5, 6, 7)
                if src_is_fp or dst_is_fp:
                    if src_is_fp:
                        src_value = fp_decode(raw_src, src_et)
                    else:
                        src_value = raw_src - (1 << src_bits) if signed_src and (raw_src & (1 << (src_bits - 1))) else raw_src
                    if dst_is_fp:
                        if isinstance(src_value, float) and math.isnan(src_value):
                            z = fp_encode(float("nan"), dst_et)
                        elif dst_et in (4, 5, 6, 7):
                            z = fp_encode(src_value, dst_et)
                        else:
                            z = int(src_value)
                            lo = -(1 << (dst_bits - 1)) if signed_src else 0
                            hi = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                            if saturate: z = min(max(z, lo), hi)
                            z &= dst_mod - 1
                    else:
                        if math.isnan(src_value) or math.isinf(src_value):
                            z = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                        else:
                            z = int(src_value)
                            lo = -(1 << (dst_bits - 1)) if signed_src else 0
                            hi = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                            if saturate: z = min(max(z, lo), hi)
                            z &= dst_mod - 1
                else:
                    src_value = raw_src - (1 << src_bits) if signed_src and (raw_src & (1 << (src_bits - 1))) else raw_src
                    if saturate:
                        lo = -(1 << (dst_bits - 1)) if signed_src else 0
                        hi = (1 << (dst_bits - 1)) - 1 if signed_src else dst_mod - 1
                        z = min(max(src_value, lo), hi)
                    else:
                        z = src_value
                    z &= dst_mod - 1
            elif op == 0x1E or op == 0x1F:
                # Strided memory uses rs1 as the base and rs2 as the
                # architectural byte stride. Each active lane is one
                # independent architectural memory access.
                width = max(1, bits // 8)
                addr = (self.read_reg(rs1) + i * self.read_reg(rs2)) & MASK64
                if op == 0x1E:
                    z = self.load_u(addr, width)
                else:
                    self.store_u(addr, width, self.vector[rd][i])
                    continue
            elif op == 0x26: z = 0
            else:
                raise CorelessTrap("vector_fault", self.pc, op)
            self.vector[rd][i] = z & ((1 << dst_bits) - 1) if op == 0x17 else z & (mod - 1)

        self.vector_vstart = 0

    def _scalar_fp_op(self, op, rd, rs1, rs2, w1):
        """Execute the Coreless-64 scalar FP baseline."""
        import math, struct
        et=(w1>>29)&7
        if et not in (4,5,6,7): raise CorelessTrap("illegal_instruction",self.pc,et)
        if ((w1 >> 8) & 7) != 0 or (self.fp_rounding & 7) != 0: raise CorelessTrap("illegal_instruction",self.pc,((w1 >> 8) & 7) or (self.fp_rounding & 7))
        def dec(raw):
            if et==4: return struct.unpack("<e",(raw&0xffff).to_bytes(2,"little"))[0]
            if et==5: return struct.unpack("<f",((raw&0xffff)<<16).to_bytes(4,"little"))[0]
            if et==6: return struct.unpack("<f",(raw&0xffffffff).to_bytes(4,"little"))[0]
            return struct.unpack("<d",(raw&MASK64).to_bytes(8,"little"))[0]
        def enc(v, typ=et):
            if typ==4: return int.from_bytes(struct.pack("<e",float(v)),"little")
            if typ==5:
                raw=int.from_bytes(struct.pack("<f",float(v)),"little"); low,high=raw&0xffff,raw>>16
                if low>0x8000 or (low==0x8000 and (high&1)): high=(high+1)&0xffff
                return high
            if typ==6: return int.from_bytes(struct.pack("<f",float(v)),"little")
            return int.from_bytes(struct.pack("<d",float(v)),"little")
        a,b=dec(self.f[rs1]),dec(self.f[rs2]); acc=dec(self.f[rd])
        try:
            if op==0: z=a+b
            elif op==1: z=a-b
            elif op==2: z=a*b
            elif op==3:
                if b==0.0 and a==0.0: z=float("nan")
                elif b==0.0: z=math.copysign(float("inf"),a*b)
                else: z=a/b
            elif op==4: z=b if math.isnan(a) else a if math.isnan(b) else (-0.0 if a == b == 0.0 else min(a,b))
            elif op==5: z=b if math.isnan(a) else a if math.isnan(b) else (0.0 if a == b == 0.0 else max(a,b))
            elif op==6: self.write_reg(rd,int(not math.isnan(a) and not math.isnan(b) and a==b)); return
            elif op==7: self.write_reg(rd,int(not math.isnan(a) and not math.isnan(b) and a<b)); return
            elif op==8: z=a*b+acc
            elif op==9: z=acc-a*b
            elif op==10: z=-a
            elif op==11: z=abs(a)
            elif op==12:
                dst=(w1>>26)&7; db=(8,16,32,64,16,16,32,64)[dst]; signed=bool(w1&1); sat=bool(w1&2)
                if dst in (4,5,6,7): self.f[rd]=enc(a,dst); return
                if math.isnan(a) or math.isinf(a): z=(1<<(db-1))-1 if signed else (1<<db)-1
                else:
                    z=int(a); lo=-(1<<(db-1)) if signed else 0; hi=(1<<(db-1))-1 if signed else (1<<db)-1
                    if sat: z=max(lo,min(hi,z))
                self.write_reg(rd,z); return
            else: raise CorelessTrap("illegal_instruction",self.pc,op)
        except (OverflowError,struct.error,ZeroDivisionError):
            raise CorelessTrap("floating_point_fault",self.pc,op)
        try:
            self.f[rd]=enc(z)
        except (OverflowError,struct.error):
            raise CorelessTrap("floating_point_fault",self.pc,op)

    def execute_vector(self, op, rd, rs1, rs2, w1):
        """Stable public boundary for architectural vector execution."""
        return self._vector_op(3, op, rd, rs1, rs2, w1)

    def execute_matrix(self, op, rd, rs1, rs2, w1, w2, w3):
        """Stable public boundary for architectural matrix execution."""
        return self._matrix_op(op, rd, rs1, rs2, w1, w2, w3)

    def _matrix_op(self, op, rd, rs1, rs2, w1, w2, w3):
        """Execute the deterministic Coreless matrix/AI baseline.

        Descriptor fields:
        - w1[31:29] input type, w1[28:26] accumulator/output type
        - w1[25:23] M/N/K shape, w1[22] signed integer mode
        - w2[15:0] / w2[31:16] row/column byte strides
        - w2[4:0] add-tile selector for MMULADD
        - w3 supplies quantization/clamp bounds.
        """
        type_bits = (8, 16, 32, 64, 16, 16, 32, 64)
        it = (w1 >> 29) & 7
        at = (w1 >> 26) & 7
        shape = (w1 >> 23) & 7
        signed_mode = bool((w1 >> 22) & 1)
        shapes = ((2, 2, 2), (4, 4, 4), (8, 8, 8),
                  (8, 16, 16), (16, 8, 16), (16, 16, 16), (32, 8, 16))
        if it >= len(type_bits) or at >= len(type_bits):
            raise CorelessTrap("matrix_ai_fault", self.pc, it)
        if shape >= len(shapes):
            raise CorelessTrap("matrix_ai_fault", self.pc, shape)
        m, n, k = shapes[shape]
        if m > 16 or n > 16 or k > 16:
            raise CorelessTrap("capability_resource_fault", self.pc, shape)
        ibits, abits = type_bits[it], type_bits[at]

        def decode_int(value, bits, signed):
            value &= (1 << bits) - 1
            if signed and value & (1 << (bits - 1)):
                return value - (1 << bits)
            return value

        def encode_int(value, bits):
            return value & ((1 << bits) - 1)

        fp_type = it >= 4 or at >= 4
        if fp_type and it != at:
            raise CorelessTrap("matrix_ai_fault", self.pc, (it << 3) | at)

        import math
        import struct

        def decode_fp(value, typ):
            if typ == 4:
                return struct.unpack("<e", (value & 0xFFFF).to_bytes(2, "little"))[0]
            if typ == 5:
                return struct.unpack("<f", ((value & 0xFFFF) << 16).to_bytes(4, "little"))[0]
            if typ == 6:
                return struct.unpack("<f", (value & 0xFFFFFFFF).to_bytes(4, "little"))[0]
            if typ == 7:
                return struct.unpack("<d", (value & MASK64).to_bytes(8, "little"))[0]
            raise CorelessTrap("matrix_ai_fault", self.pc, typ)

        def encode_fp(value, typ):
            if not math.isfinite(value):
                if typ == 4:
                    return int.from_bytes(struct.pack("<e", float(value)), "little")
                if typ == 5:
                    raw = int.from_bytes(struct.pack("<f", float(value)), "little")
                    return raw >> 16
                if typ == 6:
                    return int.from_bytes(struct.pack("<f", float(value)), "little")
                return int.from_bytes(struct.pack("<d", float(value)), "little")
            if typ == 4:
                return int.from_bytes(struct.pack("<e", float(value)), "little")
            if typ == 5:
                raw = int.from_bytes(struct.pack("<f", float(value)), "little")
                low, high = raw & 0xFFFF, raw >> 16
                if low > 0x8000 or (low == 0x8000 and (high & 1)):
                    high = (high + 1) & 0xFFFF
                return high
            if typ == 6:
                return int.from_bytes(struct.pack("<f", float(value)), "little")
            if typ == 7:
                return int.from_bytes(struct.pack("<d", float(value)), "little")
            raise CorelessTrap("matrix_ai_fault", self.pc, typ)

        def decode_value(value, bits, type_code=None):
            if fp_type:
                return decode_fp(value, it if type_code is None else type_code)
            return decode_int(value, bits, signed_mode)

        def encode_value(value, bits, type_code=None):
            if fp_type:
                return encode_fp(value, at if type_code is None else type_code)
            return encode_int(value, bits)

        def convert(value, src_bits, dst_bits, signed):
            if fp_type:
                if src_bits != dst_bits:
                    raise CorelessTrap("matrix_ai_fault", self.pc, (src_bits << 3) | dst_bits)
                return encode_fp(decode_fp(value, src_bits), dst_bits)
            return encode_int(decode_int(value, src_bits, signed), dst_bits)

        def matmul(add_tile=None):
            out = [[0 for _ in range(n)] for _ in range(m)]
            for i in range(m):
                for j in range(n):
                    acc = decode_value(self.matrix[add_tile][i][j], abits, at) if add_tile is not None else 0.0 if fp_type else 0
                    if add_tile is None and op == 0x01:
                        acc = decode_value(self.matrix[rd][i][j], abits, at)
                    for q in range(k):
                        a = decode_value(self.matrix[rs1][i][q], ibits, it)
                        b = decode_value(self.matrix[rs2][q][j], ibits, it)
                        acc += a * b
                    out[i][j] = encode_value(acc, abits, at)
            for i in range(m):
                for j in range(n):
                    self.matrix[rd][i][j] = out[i][j]

        if op in (0x00, 0x01):
            matmul()
        elif op == 0x02:
            # MMDOT is the integer dot-product form. The architectural
            # result is the same MxN dot-product matrix as MMUL, but the
            # operation is restricted to integer element types.
            if it >= 4 or at >= 4:
                raise CorelessTrap("matrix_ai_fault", self.pc, op)
            matmul()
        elif op == 0x03:
            # Reference quantized path: 8-bit integer inputs with an
            # integer accumulator. Other combinations are unsupported.
            if it not in (0, 1) or at not in (0, 1, 2, 3):
                raise CorelessTrap("matrix_ai_fault", self.pc, op)
            za = decode_int((w2 >> 0) & 0xFF, 8, signed_mode)
            zb = decode_int((w2 >> 8) & 0xFF, 8, signed_mode)
            zo = decode_int((w2 >> 16) & 0xFF, 8, signed_mode)
            shift = (w2 >> 24) & 0x3F
            lo = decode_int(w3 & 0xFFFF, 16, True)
            hi = decode_int((w3 >> 16) & 0xFFFF, 16, True)
            if lo > hi:
                raise CorelessTrap("matrix_ai_fault", self.pc, w3)
            for i in range(m):
                for j in range(n):
                    acc = decode_int(self.matrix[rd][i][j], abits, signed_mode)
                    for q in range(k):
                        a = decode_int(self.matrix[rs1][i][q], ibits, signed_mode) - za
                        b = decode_int(self.matrix[rs2][q][j], ibits, signed_mode) - zb
                        acc += a * b
                    acc = (acc >> shift) if shift else acc
                    self.matrix[rd][i][j] = encode_int(max(lo, min(hi, acc + zo)), abits)
        elif op in (0x04, 0x05):
            for i in range(m):
                for j in range(n):
                    a = decode_value(self.matrix[rs1][i][j], ibits)
                    b = decode_value(self.matrix[rs2][i][j], ibits)
                    z = a + b if op == 0x04 else a - b
                    self.matrix[rd][i][j] = encode_value(z, abits)
        elif op == 0x06:
            matmul(add_tile=w2 & 0x1F)
        elif op == 0x07:
            old = [row[:n] for row in self.matrix[rs1][:m]]
            for i in range(n):
                for j in range(m):
                    self.matrix[rd][i][j] = old[j][i]
        elif op == 0x08:
            for i in range(m):
                for j in range(n):
                    self.matrix[rd][i][j] = convert(self.matrix[rs1][i][j], ibits, abits, signed_mode)
        elif op in (0x09, 0x0A):
            elem_bytes = max(1, ibits // 8)
            row_stride = (w2 & 0xFFFF) or (n * elem_bytes)
            col_stride = ((w2 >> 16) & 0xFFFF) or elem_bytes
            displacement = w3 & 0xFFFFFFFF
            if displacement & (1 << 31):
                displacement -= 1 << 32
            base = (self.read_reg(rs1) + displacement) & MASK64
            addresses = [
                (base + i * row_stride + j * col_stride) & MASK64
                for i in range(m) for j in range(n)
            ]
            if op == 0x09:
                # Preflight every element before changing the destination
                # tile so a later fault cannot expose a partially loaded tile.
                values = [self.load_u(addr, elem_bytes) for addr in addresses]
                for index, value in enumerate(values):
                    i, j = divmod(index, n)
                    self.matrix[rd][i][j] = value
            else:
                # Validate every destination access before performing any
                # store, preserving atomic architectural retirement. Translation,
                # alignment, and physical bounds are all checked in the preflight.
                for addr in addresses:
                    if addr & (elem_bytes - 1):
                        raise CorelessTrap("alignment_fault", self.pc, addr)
                    phys = self._phys(addr, "write")
                    if phys + elem_bytes > len(self.memory):
                        raise CorelessTrap("data_access_fault", self.pc, addr)
                for index, addr in enumerate(addresses):
                    i, j = divmod(index, n)
                    self.store_u(addr, elem_bytes, self.matrix[rd][i][j])
        elif op == 0x0B:
            for i in range(m):
                for j in range(n):
                    self.matrix[rd][i][j] = 0
        elif op == 0x0C:
            value = self.read_reg(rs1)
            for i in range(m):
                for j in range(n):
                    self.matrix[rd][i][j] = encode_int(value, abits)
        elif op == 0x0D:
            total = 0
            for i in range(m):
                for j in range(n):
                    total += decode_int(self.matrix[rs1][i][j], ibits, signed_mode)
            self.write_reg(rd, total)
        elif op == 0x0E:
            # w3 is a 32-bit descriptor word: signed 16-bit lower/upper bounds.
            lo = decode_int(w3 & 0xFFFF, 16, True)
            hi = decode_int((w3 >> 16) & 0xFFFF, 16, True)
            if lo > hi:
                raise CorelessTrap("matrix_ai_fault", self.pc, w3)
            for i in range(m):
                for j in range(n):
                    value = decode_int(self.matrix[rs1][i][j], ibits, signed_mode)
                    self.matrix[rd][i][j] = encode_int(max(lo, min(hi, value)), abits)
        else:
            raise CorelessTrap("matrix_ai_fault", self.pc, op)

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
                    q = (abs(ax) // abs(ay)) * (-1 if (ax < 0) != (ay < 0) else 1)
                    z = ax - q * ay
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
        elif name in ("VM_SEND","VM_RECV","VM_GRANT","VM_REVOKE","VM_SHARE","VM_UNSHARE"):
            if self.privilege < HYPERVISOR or self.vm_handler is None:
                raise CorelessTrap("virtualization_fault", self.pc, {"VM_SEND":0,"VM_RECV":1,"VM_GRANT":2,"VM_REVOKE":3,"VM_SHARE":4,"VM_UNSHARE":5}[name])
            result = self.vm_handler(self, name, ins[1], ins[2], ins[3])
            if result is not None:
                self.write_reg(ins[1], result)
        elif name=="HALT":
            self.halted=True
        elif name=="WAIT":
            if not (self.pending_interrupts & self.csrs[0x001]):
                return "wait"
        elif name=="TRAP":
            self._enter_trap(CorelessTrap("breakpoint", self.pc, ins[3]))
            return "trap"
        elif name=="SYSCALL":
            # SYSCALL is always an architectural trap.  Enter supervisor
            # state first, then let privileged software service the trap.
            trap = CorelessTrap("syscall", self.pc, ins[3])
            self._enter_trap(trap)
            if self.supervisor_trap_handler is not None:
                self.supervisor_trap_handler(self, trap)
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
            if self.privilege < MACHINE:
                raise CorelessTrap("privilege_violation", self.pc, 0)
            self.tlb.clear()
        elif name=="TLBFLUSHVA":
            addr_reg = ins[2] if len(ins) > 2 else ins[1]
            if self.privilege < MACHINE:
                raise CorelessTrap("privilege_violation", self.pc, self.read_reg(addr_reg))
            self.tlb.pop(self.read_reg(addr_reg) >> 12, None)
        elif name=="READCSR":
            self.write_reg(ins[1], self.read_csr(ins[3] & 0xFFFF))
        elif name=="WRITECSR":
            self.write_csr(ins[3] & 0xFFFF, self.read_reg(ins[2]))
        else:
            raise CorelessTrap("illegal_instruction", self.pc)
        return next_pc

    def _record_step_result(self, event, pc, cause=None, tval=0):
        """Record the architectural outcome of the most recent step."""
        self._last_step_result = {
            "event": event,
            "pc": pc & MASK64,
            "cause": cause,
            "tval": tval,
        }

    @property
    def last_step_result(self):
        """Return a copy of the most recent step outcome."""
        return dict(self._last_step_result)

    def _fetch_instruction(self):
        """Fetch exactly one architectural instruction from the current PC.

        The first word determines the total length; payload words are fetched
        only after that boundary is known. Execute permissions and bounds are
        therefore checked for the complete instruction before execution.
        """
        from encoding import instruction_length
        first = self.load_u(self.pc, 4, execute=True)
        length = instruction_length(first)
        words = [first]
        for offset in range(4, length, 4):
            words.append(self.load_u(self.pc + offset, 4, execute=True))
        return length, words

    def step(self):
        self._last_step_event = None
        start_pc = self.pc
        if self.halted:
            self._last_step_event = "halt"
            self._record_step_result("halt", start_pc)
            return False
        if self._take_interrupt_if_enabled():
            self._last_step_event = "interrupt"
            self._record_step_result("interrupt", start_pc)
            return True
        
            return True
        from encoding import from_bytes, instruction_length, decode, IllegalEncoding
        try:
            length, words = self._fetch_instruction()
            first = words[0]
            self._last_word = first
            if length in (8, 16):
                from encoding import decode_extended_header
                h = decode_extended_header(first)
                cls, op, rd, rs1, rs2, fmt = h
                if fmt != 2:
                    raise CorelessTrap("instruction_encoding_fault", self.pc, fmt)
                if length == 8:
                    # The 64-bit form is the compact extended envelope. The
                    # first implemented 64-bit family is scalar FP: its single
                    # payload word contains the complete FP descriptor.
                    if cls != 2 or not 0 <= op <= 12:
                        raise CorelessTrap("illegal_instruction", self.pc, op)
                    self._scalar_fp_op(op, rd, rs1, rs2, words[1])
                elif cls == 2:
                    self._scalar_fp_op(op, rd, rs1, rs2, words[1])
                elif cls == 3:
                    self._vector_op(cls, op, rd, rs1, rs2, words[1])
                elif cls == 4:
                    self._matrix_op(op, rd, rs1, rs2, words[1], words[2], words[3])
                else:
                    raise CorelessTrap("illegal_instruction", self.pc, cls)
                next_pc = (self.pc + length) & MASK64
            else:
                ins = decode(first)
                next_pc = self._execute(ins)
            if next_pc == "wait":
                self._last_step_event = "wait"
                self._record_step_result("wait", start_pc)
                self.r[0] = 0
                return True
            if next_pc == "trap":
                self._last_step_event = "trap"
                self._record_step_result("trap", start_pc, self.csrs[0x005] & 0xFFFF, self.csrs[0x006])
                self.r[0] = 0
                return True
            if next_pc & 3:
                raise CorelessTrap("alignment_fault", self.pc, next_pc)
            self.r[0] = 0
            self.pc = next_pc & MASK64
            self.cycle += 1
            self.instret += 1
            self._last_step_event = "halt" if self.halted else "retired"
            self._record_step_result(self._last_step_event, start_pc)
            return True
        except IllegalEncoding:
            trap = CorelessTrap("illegal_instruction", self.pc, 0)
            self._enter_trap(trap)
            self._last_step_event = "trap"
            self._record_step_result("trap", start_pc, self.csrs[0x005] & 0xFFFF, self.csrs[0x006])
            return True
        except CorelessTrap as trap:
            self._enter_trap(trap)
            if trap.cause == "syscall" and self.supervisor_trap_handler is not None:
                self.supervisor_trap_handler(self, trap)
            self._last_step_event = "trap"
            self._record_step_result("trap", start_pc, self.csrs[0x005] & 0xFFFF, self.csrs[0x006])
            return True


    def load_program(self, program, address=0):
        """Load an architectural instruction stream into Coreless memory.

        program may be bytes-like data containing variable-length Coreless-64
        instructions. The stream is copied without decoding it; instruction
        boundaries remain the responsibility of the architectural fetch/decode path.
        """
        data = bytes(program)
        if address < 0 or address + len(data) > len(self.memory):
            raise ValueError("program does not fit in Coreless memory")
        self.memory[address:address + len(data)] = data
        self.pc = address & MASK64
        return len(data)

    def run(self, max_steps=100000):
        """Run from the current PC until HALT, trap, wait, or the step limit."""
        if max_steps < 0:
            raise ValueError("max_steps must be non-negative")
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
            if self.last_step_result["event"] in ("halt", "trap", "wait", "interrupt"):
                break
        return steps
