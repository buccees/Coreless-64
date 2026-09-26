# Coreless Native System Calls

Coreless programs enter the operating system with the `SYSCALL` instruction.

## Calling convention

- R1: return value
- R2: syscall argument 0
- R3: syscall argument 1
- R4: syscall argument 2
- R5: syscall argument 3
- R6: syscall argument 4
- R7: syscall argument 5
- syscall number: 11-bit immediate in `SYSCALL`

A negative R1 value represents a reference-model error. Exact error numbers will be frozen with the ABI.

## Initial calls

0 exit
1 read
2 write
3 open
4 close
5 seek
6 stat
7 sleep
8 yield
9 spawn
10 exec
11 wait
12 kill
13 getpid
14 time
15 memory
16 cpu_info
17 device_info
18 net_send
19 net_recv
20 socket
21 connect
22 listen
23 accept
24 display_open
25 display_present
26 input_read
27 checkpoint
28 capability

The namespace is versioned by the Coreless ABI. Reserved numbers must not be reused without an ABI revision.

The syscall boundary is architectural: a native implementation may dispatch directly in hardware or through a privileged software layer, but the program-visible contract remains the same.
