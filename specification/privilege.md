# Coreless-64 Privilege Architecture

**Version:** 0.1  
**Status:** Draft

## Modes

Coreless-64 defines four primary privilege domains:

1. User
2. Supervisor
3. Hypervisor
4. Machine/Firmware

User software cannot directly access privileged resources.

Supervisor mode controls the Coreless operating system.

Hypervisor mode controls guest machines.

Machine/Firmware mode controls boot, hardware discovery, low-level machine services, and recovery.

## Protection

Privilege controls access to:

- memory mappings
- interrupts
- timers
- devices
- CPU control
- virtualization
- machine configuration
- security state

## Exceptions

Synchronous exceptions transfer control to a privileged handler with saved fault information.

## Interrupts

Interrupt enable state and interrupt routing are privileged.

## Virtualization

A hypervisor may create guest CPU contexts, guest address spaces, virtual interrupts, and virtual devices.

## Secure boot

The architecture will support a chain of trust beginning in a machine root of trust where hardware provides one.

Secure boot is not required for the reference emulator but must be representable architecturally.

## Principle

Privilege is an architectural isolation boundary, not merely an OS convention.


## MMU Privilege Rules

Translation roots, page-table configuration, address-space controls, and TLB invalidation are privileged operations.

- User mode cannot modify the active translation root.
- Supervisor mode controls ordinary process address spaces.
- Hypervisor mode controls guest translation domains.
- Machine mode controls implementation-wide MMU configuration.

Translation faults enter the normal precise exception mechanism.

### Address-space transitions

A context switch may change the active translation root and associated address-space identifier. Tagged translations may be retained across switches when architectural isolation is preserved.


## Architectural CSR Map

CSR numbers are 16-bit identifiers. The following baseline map is normative for Coreless-64 v0.x.

| CSR | Name | Access | Purpose |
|---:|---|---|---|
| 0x000 | STATUS | RW | current privilege and machine status |
| 0x001 | IE | RW | interrupt-enable state |
| 0x002 | IP | RW | interrupt-pending state |
| 0x003 | TVEC | RW | trap-vector base |
| 0x004 | EPC | RW | exception PC |
| 0x005 | CAUSE | R | exception/interrupt cause |
| 0x006 | TVAL | RW | trap value/fault value |
| 0x007 | ROOT | RW | active translation root |
| 0x008 | ASID | RW | address-space identifier |
| 0x009 | TLBCTL | RW | translation-control state |
| 0x00A | CPU_ID | R | architectural CPU identifier |
| 0x00B | CPU_COUNT | R | discovered execution-context count |
| 0x00C | CAP_BASE | R | capability-discovery base |
| 0x00D | TIME | R | architectural time counter |
| 0x00E | CYCLE | R | implementation cycle counter |
| 0x00F | INSTRET | R | retired-instruction counter |
| 0x010 | FSTATUS | RW | floating-point status |
| 0x011 | VSTART | RW | vector restart index |
| 0x012 | VL | RW | active vector length |
| 0x013 | VTYPE | RW | vector type/control |
| 0x014 | VCSR | RW | vector control/status |
| 0x015 | MSTATUS | RW | matrix/AI status |
| 0x016 | VMSPEC | R | virtualization capability/state |
| 0x017 | VROOT | RW | guest second-stage root |
| 0x018 | VMID | RW | current virtualization domain |
| 0x019 | VMCTL | RW | virtualization control |
| 0x01A | IBASE | RW | interrupt-controller configuration |
| 0x01B | IPRIO | RW | interrupt priority state |
| 0x01C | FENCECTL | RW | implementation memory-order control |
| 0x01D | BOOT_STATUS | R | boot/security state |
| 0x01E | MACHINE_CFG | RW | machine configuration pointer/control |
| 0x01F | ARCH_ID | R | Coreless-64 architecture identifier |

CSR numbers 0x020–0x0FF are reserved for future architectural state. 0x100–0x7FF are extension-defined. 0x800–0xFFF are implementation-defined and must be capability-discoverable.

Writes to read-only CSRs are illegal. Access to a CSR below its required privilege raises a privilege exception. Reserved fields read as zero and must be written as zero unless a future revision assigns them.
