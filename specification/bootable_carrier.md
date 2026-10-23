# Bootable Coreless carrier image

## First boot target

The first bootable carrier target is a **UEFI x86_64 SSD image**. It uses a small Debian bootstrap environment to initialize physical hardware and launch the Coreless digital execution engine already stored on the SSD. The disk uses three GPT partitions: a UEFI EFI System Partition, a Debian bootstrap root filesystem, and a dedicated `CORELESS_STATE` ext4 partition mounted at `/var/lib/coreless`. The Coreless persistent machine image lives at `/var/lib/coreless/coreless.img`, and the VIGIL registry lives at `/var/lib/coreless/vigil-spatial.sqlite3`. This keeps machine and spatial state separate from the bootstrap root filesystem so root-image replacement does not inherently overwrite them. The boot-time console sends commands to the Coreless OS shell rather than to the Linux shell. At startup it also opens the carrier-owned VIGIL registry at `/var/lib/coreless/vigil-spatial.sqlite3` and restores the active spatial model, regions, expected-sensor coverage, last-known tracks, sensor lifecycle history, and alert acknowledgements when present. The registry database is separate from the machine checkpoint image, while both live on the dedicated state partition.

This is an initial bootable carrier and integration milestone, not a claim that the current Python reference engine is already a native bare-metal Coreless kernel or that every PC/SSD combination has been validated. The Coreless machine, OS model, execution engine, and persistent state remain Coreless-owned; the Linux kernel is currently the bootstrap and physical-device driver substrate for this first hardware bring-up. Replacing that substrate with a native Coreless boot chain remains future work.

## Build an image

On an x86_64 Debian/Ubuntu Linux build machine with network access, install the image-build tools:

```bash
sudo apt-get update
sudo apt-get install -y debootstrap parted util-linux dosfstools e2fsprogs rsync
```

Then from the repository checkout:

```bash
bash scripts/build-bootable-ssd.sh
```

The default output is `dist/coreless-uefi-x86_64.img`, a sparse 16 GiB disk image. The current partition layout assigns 1 MiB–513 MiB to EFI, 513 MiB–70% to bootstrap root, and 70%–100% to `CORELESS_STATE`. Set `CORELESS_DISK_SIZE` to change its capacity, `CORELESS_DEBIAN_SUITE` to select a supported Debian suite, or pass a different output path as the first argument. The build requires sudo, network access, and sufficient free space; it does not write to a physical SSD.

## Boot and operate

1. Build the image and verify the resulting file before use.
2. Write the image to a dedicated SSD using a trusted disk-imaging utility. **Writing the image erases the selected target disk.** Double-check the destination device; never select the computer's internal system disk.
3. Boot a compatible x86_64 computer in UEFI mode from that SSD. Secure Boot compatibility is not yet promised; disable Secure Boot for this prototype if the firmware rejects the unsigned boot chain.
4. The system starts the Coreless machine console on the first virtual terminal. Commands are routed to the Coreless OS shell.

Console commands:

- `:status` — show the Coreless machine and boot status.\n- `:spatial` — show the active VIGIL model, restored last-known track count, persisted sensor lifecycle event count, and alert acknowledgement count.
- `:checkpoint [name]` — persist a named machine checkpoint.
- `:help` — show console commands.
- `:shutdown` — persist state and shut down the console cleanly.

The first image targets UEFI x86_64. Legacy BIOS, ARM64, Secure Boot signing, broad storage-controller compatibility, automatic graphical display/input transports, and physical hardware enumeration as a separate USB computer are not yet implemented or validated. A conventional SSD enclosure cannot become an independent USB computer without suitable device-side hardware.

## Validation status

The carrier startup wiring has a deterministic restart test for restoration of the active VIGIL model, sensor lifecycle history, and alert acknowledgements. Last-known tracks are restored as reacquisition-required evidence rather than asserted live contact. CI can check script syntax and Python-level restoration, but only building the full image and booting it on real hardware or a representative UEFI virtual machine can validate the end-to-end carrier. Do not describe the image as field-tested until that test has passed.
