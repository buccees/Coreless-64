# Coreless Process Address Spaces

Each process has an explicit address-space object in the reference runtime. The object records a process region, executable/code base, stack region, size, and baseline permissions.

The reference scheduler saves and restores architectural registers and PC at process boundaries and assigns each process a private logical region. The current reference implementation uses a single backing memory array, so this is a model of the architectural boundary rather than a complete hardware MMU isolation implementation.

The next native implementation step is to map these process regions through Coreless page tables and enforce user/supervisor permissions during every instruction and data access.

## Initial userspace

The OS exposes `start_init()` to create the `/init` process as PID 1. Boot firmware remains separate from userspace initialization.
