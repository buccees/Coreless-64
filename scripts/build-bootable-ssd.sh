#!/usr/bin/env bash
# Build a UEFI-bootable x86_64 Coreless carrier disk image.
# This creates a NEW image file; it never writes to a physical SSD.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist/coreless-uefi-x86_64.img}"
SIZE="${CORELESS_DISK_SIZE:-16G}"
SUITE="${CORELESS_DEBIAN_SUITE:-bookworm}"
MIRROR="${CORELESS_DEBIAN_MIRROR:-https://deb.debian.org/debian}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/coreless-image.XXXXXX")"
LOOP=""
MOUNTED=()

cleanup() {
  for ((i=${#MOUNTED[@]}-1; i>=0; i--)); do
    target="${MOUNTED[$i]}"
    mountpoint -q "$target" && sudo umount "$target" || true
  done
  if [[ -n "$LOOP" ]]; then sudo losetup -d "$LOOP" 2>/dev/null || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required tool: $1" >&2; exit 2; }; }
for tool in sudo debootstrap parted losetup mkfs.vfat mkfs.ext4 mount chroot rsync; do need "$tool"; done
[[ "$(uname -m)" == "x86_64" ]] || { echo "Build on x86_64 Linux for the first UEFI target." >&2; exit 2; }
[[ "$EUID" -ne 0 ]] || { echo "Run as a normal user with sudo; output is a regular image file." >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo "Refusing to overwrite existing output: $OUT" >&2; exit 2; }

OUT="$(mkdir -p "$(dirname "$OUT")" && cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
mkdir -p "$WORK/root"
sudo truncate -s "$SIZE" "$OUT"
sudo parted -s "$OUT" mklabel gpt
sudo parted -s "$OUT" mkpart ESP fat32 1MiB 513MiB
sudo parted -s "$OUT" set 1 esp on
sudo parted -s "$OUT" mkpart CORELESS ext4 513MiB 70%\nsudo parted -s "$OUT" mkpart CORELESS_STATE ext4 70% 100%
LOOP="$(sudo losetup --find --show --partscan "$OUT")"
sudo partprobe "$LOOP" 2>/dev/null || true
for _ in $(seq 1 20); do [[ -b "${LOOP}p2" ]] && break; sleep 0.25; done
[[ -b "${LOOP}p1" && -b "${LOOP}p2" && -b "${LOOP}p3" ]] || { echo "Partition devices were not created for $LOOP" >&2; exit 1; }

sudo mkfs.vfat -F 32 -n CORELESSEFI "${LOOP}p1"
sudo mkfs.ext4 -F -L CORELESS_ROOT "${LOOP}p2"\nsudo mkfs.ext4 -F -L CORELESS_STATE "${LOOP}p3"
sudo mount "${LOOP}p2" "$WORK/root"; MOUNTED+=("$WORK/root")
sudo mkdir -p "$WORK/root/boot/efi"
sudo mount "${LOOP}p1" "$WORK/root/boot/efi"; MOUNTED+=("$WORK/root/boot/efi")

sudo debootstrap --arch=amd64 "$SUITE" "$WORK/root" "$MIRROR"
sudo mkdir -p "$WORK/root/dev" "$WORK/root/proc" "$WORK/root/sys" "$WORK/root/run"
for dir in dev proc sys run; do sudo mount --bind "/$dir" "$WORK/root/$dir"; MOUNTED+=("$WORK/root/$dir"); done

sudo install -m 0644 /dev/null "$WORK/root/etc/hostname"
echo coreless-64 | sudo tee "$WORK/root/etc/hostname" >/dev/null
sudo tee "$WORK/root/etc/hosts" >/dev/null <<'EOF'
127.0.0.1 localhost
127.0.1.1 coreless-64
::1 localhost ip6-localhost ip6-loopback
EOF
ROOT_UUID="$(sudo blkid -s UUID -o value "${LOOP}p2")"
EFI_UUID="$(sudo blkid -s UUID -o value "${LOOP}p1")"\nSTATE_UUID="$(sudo blkid -s UUID -o value "${LOOP}p3")"
sudo tee "$WORK/root/etc/fstab" >/dev/null <<EOF
UUID=$ROOT_UUID / ext4 defaults,noatime 0 1
UUID=$EFI_UUID /boot/efi vfat umask=0077 0 1
EOF

sudo chroot "$WORK/root" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/bash -euxc '
  apt-get update
  apt-get install -y --no-install-recommends linux-image-amd64 grub-efi-amd64 systemd-sysv python3 openssl ca-certificates iproute2 network-manager sudo
  ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
  printf "LANG=C.UTF-8\n" >/etc/default/locale
  printf "GRUB_TIMEOUT=3\nGRUB_DISTRIBUTOR=Coreless-64\nGRUB_DISABLE_OS_PROBER=true\n" >/etc/default/grub
  grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=CORELESS --removable --no-nvram
  update-grub
'

sudo mkdir -p "$WORK/root/opt/coreless" "$WORK/root/var/lib/coreless"\nsudo mount "${LOOP}p3" "$WORK/root/var/lib/coreless"; MOUNTED+=("$WORK/root/var/lib/coreless")
sudo rsync -a --delete   --exclude=.git --exclude=dist --exclude='*.img' --exclude='*.lock'   --exclude='__pycache__' --exclude='.pytest_cache'   "$ROOT/" "$WORK/root/opt/coreless/"
sudo install -m 0644 "$ROOT/deploy/coreless-machine.service" "$WORK/root/etc/systemd/system/coreless-machine.service"
sudo systemctl --root="$WORK/root" disable getty@tty1.service
sudo systemctl --root="$WORK/root" enable NetworkManager.service coreless-machine.service
sudo systemctl --root="$WORK/root" set-default multi-user.target
sudo sync
sudo umount "$WORK/root/run" "$WORK/root/sys" "$WORK/root/proc" "$WORK/root/dev" "$WORK/root/var/lib/coreless" "$WORK/root/boot/efi" "$WORK/root"
MOUNTED=()
sudo losetup -d "$LOOP"
LOOP=""
sudo chown "$(id -u):$(id -g)" "$OUT"
echo "Bootable Coreless carrier image created: $OUT"
echo "Target: x86_64 UEFI; Debian $SUITE; GPT + EFI System Partition + ext4 root + dedicated CORELESS_STATE partition mounted at /var/lib/coreless."
echo "The image file is new and was not written to a physical disk."
echo "Use a disk-imaging tool to write this image to a dedicated SSD; that target operation erases the SSD."
