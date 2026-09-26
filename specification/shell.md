# Coreless Native Shell

The Coreless native shell is the primary human command interface for the reference operating environment. It is intentionally familiar to users of Unix-like systems without making Coreless a Unix or Linux clone.

## Core commands

- `help` — list available commands
- `clear` — clear the terminal
- `exit` / `quit` — leave the shell
- `pwd` — print the current directory
- `ls [PATH]` — list filesystem entries
- `cd [PATH]` — change directory
- `cat PATH` — display a text file
- `write PATH TEXT` — create or replace a text file
- `rm PATH` — remove a file

## Process commands

- `run PROGRAM` — load and execute a Coreless program as a process
- `ps` — list processes
- `kill PID` — mark a process killed

## Machine commands

- `status` — show operating-environment status
- `boot` — initialize and boot the machine
- `cpu` — show CPU/execution-context information
- `memory` — show memory capacity
- `devices` — enumerate discovered devices
- `storage` — show persistent storage object count
- `checkpoint [NAME]` — save persistent machine state

## Network commands

- `net` — show network state
- `net config` — show network configuration
- `net config ipv4 ADDRESS [ipv6 ADDRESS] [hostname NAME]` — configure the network service
- `net ping TARGET` — transmit a Coreless ping frame
- `net rx` — receive the next queued packet

## Desktop commands

- `desktop` — show display/desktop state
- `open TITLE [WIDTH HEIGHT]` — create a window
- `windows` — list windows
- `events` — read pending input events

## Design rule

These commands are a **native Coreless interface**. Familiar names are chosen for usability, but their semantics are defined by Coreless services and the Coreless ABI rather than inherited from Linux, Windows, or another operating system.

The command interpreter is therefore replaceable: the same operating-system services can later be driven by a graphical terminal, remote console, automation interface, or native application.

## Current implementation

The reference implementation provides the command interpreter in `reference/shell.py` and the booted service environment in `reference/os_runtime.py`. The command set will grow as the Coreless ABI, filesystem, process model, networking, graphics, security, and compatibility layers mature.
