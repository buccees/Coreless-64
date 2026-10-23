#!/usr/bin/env bash
# Read-only structural validation for a newly built Coreless carrier image.
set -Eeuo pipefail

IMAGE="${1:?Usage: validate-bootable-ssd.sh IMAGE}"
[[ -f "$IMAGE" ]] || { echo "Image not found: $IMAGE" >&2; exit 2; }
for tool in sudo losetup partprobe lsblk blkid mount umount findmnt; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing required tool: $tool" >&2; exit 2; }
done

WORK="$(mktemp -d "${TMPDIR:-/tmp}/coreless-validate.XXXXXX")"
LOOP=""
MOUNTED=()
cleanup() {
  for ((i=${#MOUNTED[@]}-1; i>=0; i--)); do
    sudo umount "${MOUNTED[$i]}" 2>/dev/null || true
  done
  if [[ -n "$LOOP" ]]; then sudo losetup -d "$LOOP" 2>/dev/null || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT

LOOP="$(sudo losetup --find --show --partscan "$IMAGE")"
sudo partprobe "$LOOP" 2>/dev/null || true
for _ in $(seq 1 20); do
  [[ -b "${LOOP}p1" && -b "${LOOP}p2" && -b "${LOOP}p3" ]] && break
  sleep 0.25
done
[[ -b "${LOOP}p1" && -b "${LOOP}p2" && -b "${LOOP}p3" ]] || {
  echo "Expected three GPT partition devices for $LOOP" >&2; exit 1;
}

label1="$(sudo blkid -s PARTLABEL -o value "${LOOP}p1")"
label2="$(sudo blkid -s PARTLABEL -o value "${LOOP}p2")"
label3="$(sudo blkid -s PARTLABEL -o value "${LOOP}p3")"
[[ "$label1" == EFI_SYSTEM && "$label2" == CORELESS && "$label3" == CORELESS_STATE ]] || {
  echo "Unexpected partition labels: $label1 / $label2 / $label3" >&2; exit 1;
}

ROOT_UUID="$(sudo blkid -s UUID -o value "${LOOP}p2")"
EFI_UUID="$(sudo blkid -s UUID -o value "${LOOP}p1")"
STATE_UUID="$(sudo blkid -s UUID -o value "${LOOP}p3")"
sudo mkdir -p "$WORK/root" "$WORK/efi" "$WORK/state"
sudo mount -o ro,noload "${LOOP}p2" "$WORK/root"; MOUNTED+=("$WORK/root")
sudo mount -o ro "${LOOP}p1" "$WORK/efi"; MOUNTED+=("$WORK/efi")
sudo mount -o ro,noload "${LOOP}p3" "$WORK/state"; MOUNTED+=("$WORK/state")

grep -Fqx "UUID=$ROOT_UUID / ext4 defaults,noatime 0 1" "$WORK/root/etc/fstab"
grep -Fqx "UUID=$EFI_UUID /boot/efi vfat umask=0077 0 1" "$WORK/root/etc/fstab"
grep -Fqx "UUID=$STATE_UUID /var/lib/coreless ext4 defaults,noatime 0 2" "$WORK/root/etc/fstab"
[[ -s "$WORK/efi/EFI/BOOT/BOOTX64.EFI" ]] || {
  echo "Missing removable-media UEFI fallback loader EFI/BOOT/BOOTX64.EFI" >&2; exit 1;
}
compgen -G "$WORK/root/boot/vmlinuz-*" >/dev/null || {
  echo "No Linux kernel image found under /boot" >&2; exit 1;
}
[[ -L "$WORK/root/etc/systemd/system/multi-user.target.wants/coreless-machine.service" && -f "$WORK/root/etc/systemd/system/coreless-machine.service" ]] || {
  echo "Coreless machine service is not enabled for multi-user.target" >&2; exit 1;
}
[[ -f "$WORK/root/opt/coreless/scripts/coreless-console.py" ]] || {
  echo "Coreless console is missing from the root filesystem" >&2; exit 1;
}

echo "PASS: GPT partition labels, filesystem UUID mounts, UEFI fallback loader, Linux kernel, enabled Coreless service, and console payload verified."
echo "This is offline image-structure validation; it does not claim a successful virtual or physical boot."
