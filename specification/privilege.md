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
