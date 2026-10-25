# Create a Coreless-64 disk image from your own fork

This guide starts from a GitHub fork and produces a **disk-image file** on your computer. Building the image does **not** write to, format, or erase a physical USB drive. Writing the finished image to a drive is a separate, destructive step and is intentionally not part of the build instructions.

## 1. Fork the repository on GitHub

1. Sign in to GitHub and open [buccees/Coreless-64](https://github.com/buccees/Coreless-64).
2. Select **Fork**, choose your account as the owner, and create the fork.
3. Open your fork and copy its HTTPS clone URL. It should look like `https://github.com/YOUR-ACCOUNT/Coreless-64.git`.

A fork is your own repository copy. Changes you make there do not automatically change the original project.

## 2. Prepare the build environment

The current image builder targets **x86-64 Linux**. On Windows, use **WSL2 with Ubuntu** and run the commands inside Ubuntu, not PowerShell. Keep the checkout in the Linux home directory (for example, `~/src/Coreless-64`) rather than under `/mnt/c` for better filesystem behavior.

In Ubuntu/WSL2, install Git and the image-building dependencies:

```bash
sudo apt-get update
sudo apt-get install -y git debootstrap parted util-linux dosfstools e2fsprogs rsync
```

If WSL2 is not installed, open PowerShell as an administrator and run `wsl --install -d Ubuntu`, restart if Windows requests it, launch Ubuntu, and finish its first-run username setup. Then run the Ubuntu commands above. On native Ubuntu x86-64, just use the terminal.

## 3. Clone your fork

Replace `YOUR-ACCOUNT` with your GitHub account name:

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/YOUR-ACCOUNT/Coreless-64.git
cd Coreless-64
git remote -v
```

The `origin` remote should point to your fork. If you need a particular feature branch, fetch and check it out explicitly:

```bash
git fetch origin
git branch -a
git switch BRANCH-NAME
git pull --ff-only
```

Replace `BRANCH-NAME` with the branch you intend to build. If you want the fork's default branch, skip those three branch commands. Before building, confirm the source revision:

```bash
git status --short --branch
git log -1 --oneline
```

## 4. Build a new image file

From the repository root:

```bash
bash scripts/build-bootable-ssd.sh
```

By default, the script creates:

```text
dist/coreless-uefi-x86_64.img
```

The default image capacity is 16 GiB. The builder requires network access, `sudo`, and enough free working space to build a Debian-based UEFI x86-64 carrier. It refuses to overwrite an existing output file. **It creates a regular image file and does not select or write to a physical disk.**

To choose a different new output path:

```bash
bash scripts/build-bootable-ssd.sh "$HOME/coreless-uefi-x86_64.img"
```

To change the image capacity, for example to 24 GiB:

```bash
CORELESS_DISK_SIZE=24G bash scripts/build-bootable-ssd.sh "$HOME/coreless-uefi-x86_64.img"
```

Build capacity is the virtual disk's capacity; it is not a command to resize or write a physical drive. Choose an output filename that does not already exist.

## 5. Validate the image file

If the validation script is present in your checkout, run:

```bash
bash scripts/validate-bootable-ssd.sh dist/coreless-uefi-x86_64.img
```

If you used a custom output path, pass that exact path instead. A successful build/validation checks the generated image structure; it does not guarantee that every physical computer will boot it. CI's QEMU/UEFI test is a separate automated virtual-machine check. Secure Boot, ARM devices, legacy BIOS, and broad physical hardware compatibility are not currently promised.

You can also record the exact source commit used for the image:

```bash
git rev-parse HEAD
sha256sum dist/coreless-uefi-x86_64.img
```

Keep the commit ID and checksum with the image so you can identify which fork revision produced it.

## 6. Only if you later choose to write it to a USB/SSD

**Warning: writing a disk image erases the selected destination drive.** The build steps above have not touched your USB drive. Do not proceed unless you deliberately want to replace the drive's contents.

When you are ready, use a trusted imaging utility such as balenaEtcher or a disk-image writing tool you understand. Select the generated `.img` file as the source and the intended removable drive as the destination; verify the drive's capacity and identity in the utility before confirming. Never choose your computer's internal system disk. Do not use a command copied from an example with a guessed `/dev/sdX` or disk number—device names vary and choosing the wrong one can destroy data.

After writing, safely eject the drive and boot a compatible x86-64 computer in UEFI mode from it. This carrier is a transitional Linux-bootstrap build that starts the current Coreless reference engine; it is not yet proof of a native bare-metal Coreless-only boot.

## Troubleshooting

- **`debootstrap: command not found` or another missing tool:** rerun the dependency-install command in step 2.
- **Permission or mount errors:** run the build from a normal user account with working `sudo`; do not run the whole script as root.
- **Network or mirror errors:** check connectivity and rerun the build after fixing it.
- **Output already exists:** choose a new filename. The script intentionally refuses to overwrite an existing image.
- **Not on x86-64 Linux:** use an x86-64 Ubuntu/WSL2 environment; the current builder rejects other architectures.
