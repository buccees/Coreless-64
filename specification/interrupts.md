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
