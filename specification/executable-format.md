# COREX64 Executable Format

The reference runtime defines a minimal executable container named COREX64.

Header:
- bytes 0-7: ASCII magic `COREX64\\0`
- bytes 8-9: little-endian version
- bytes 10-13: little-endian entry offset
- bytes 14-15: little-endian code size

The payload begins immediately after the 16-byte header and contains Coreless-64 encoded instructions.

The loader validates the complete instruction stream before loading it. The architectural entry address is load address plus the entry offset.

This is a bootstrap format. A future executable ABI can add segments, permissions, relocations, imports, signatures, debug metadata, and architecture feature requirements without changing the Coreless instruction architecture.
