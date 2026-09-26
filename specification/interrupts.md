# Coreless-64 Interrupts and Exceptions

**Version:** 0.1  
**Status:** Draft

## Event classes

Coreless distinguishes:

- synchronous exceptions
- faults
- traps
- asynchronous interrupts
- inter-processor interrupts

## Sources

Interrupts may originate from:

- timers
- storage
- network
- display/input
- GPU
- vector engine
- AI engine
- inter-CPU signaling
- external interfaces

## Interrupt controller

The interrupt architecture must support large CPU counts and programmable routing.

Each interrupt has:

- source
- priority
- target
- enable state
- pending state
- privilege target

## Inter-processor interrupts

CPUs can signal one another for scheduling, TLB coordination, synchronization, and other OS functions.

## Exception state

A trap records enough architectural state to restart, terminate, or emulate the faulting operation.

The exact register layout is frozen in the final privileged specification.


## Multiprocessor Interrupt Coordination

Interrupt targeting includes a destination CPU ID or implementation-defined broadcast class. IPIs are ordered according to the interrupt architecture and become pending independently on each destination context.

TLB shootdowns use IPIs or an equivalent architectural mechanism so that stale translations are invalidated on affected contexts before software relies on the new mapping.


## Exception and Interrupt Cause Encoding

`CAUSE` is a 64-bit architectural value. Bit 63 distinguishes interrupts from synchronous exceptions: 0 = exception, 1 = interrupt. Bits 62:56 encode the privilege domain that received the event. Bits 55:0 contain the cause code.

### Synchronous exception codes

| Code | Exception |
|---:|---|
| 0x000 | instruction access fault |
| 0x001 | instruction page fault |
| 0x002 | illegal instruction |
| 0x003 | illegal CSR |
| 0x004 | privilege violation |
| 0x005 | breakpoint |
| 0x006 | alignment fault |
| 0x007 | data access fault |
| 0x008 | data page fault |
| 0x009 | execute permission fault |
| 0x00A | write permission fault |
| 0x00B | read permission fault |
| 0x00C | malformed translation |
| 0x00D | invalid memory attribute |
| 0x00E | arithmetic fault |
| 0x00F | floating-point fault |
| 0x010 | vector fault |
| 0x011 | matrix/AI fault |
| 0x012 | virtualization fault |
| 0x013 | second-stage translation fault |
| 0x014 | capability/resource fault |
| 0x015 | device fault |
| 0x016 | machine-check fault |
| 0x017 | instruction encoding fault |
| 0x018–0x0FF | reserved |

### Interrupt codes

| Code | Interrupt |
|---:|---|
| 0x000 | software interrupt |
| 0x001 | timer interrupt |
| 0x002 | external/device interrupt |
| 0x003 | inter-processor interrupt |
| 0x004 | performance/monitor interrupt |
| 0x005 | machine fault interrupt |
| 0x006–0x0FF | reserved |

Exception codes and interrupt codes occupy separate namespaces because bit 63 identifies the event class.

### Priority

Synchronous faults caused by the current instruction are reported before later asynchronous interrupts. Among pending interrupts, the highest enabled architectural priority is selected. Equal-priority interrupts use implementation-defined deterministic arbitration.


## Trap Entry and Return State

On synchronous exception or interrupt entry, the machine saves the faulting or interrupted PC in EPC, writes the event cause to CAUSE, and writes the relevant fault address or value to TVAL. The current interrupt-enable and privilege state are preserved in architectural status state before control transfers to TVEC.

The handler begins at the vector selected by TVEC and the event cause. Implementations may use direct or vectored dispatch according to the configured interrupt mode.

RETX restores the saved privilege and interrupt state and resumes at EPC. The handler may modify EPC when intentionally skipping or redirecting execution.

For faults on restartable instructions, EPC identifies the instruction that must be retried unless the architectural instruction explicitly defines a different restart point. Vector restart uses VSTART where applicable.

Interrupt entry is precise with respect to retired state. No later instruction may become architecturally retired before the interrupted instruction boundary.
