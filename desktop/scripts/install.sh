#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-/dev/sda}"
parted -s "$DEVICE" mklabel gpt
parted -s "$DEVICE" mkpart ESP fat32 1MiB 513MiB
parted -s "$DEVICE" set 1 esp on
parted -s "$DEVICE" mkpart ROOT ext4 513MiB 100%
mkfs.vfat "${DEVICE}1"
mkfs.ext4 "${DEVICE}2"
mount "${DEVICE}2" /mnt
mkdir -p /mnt/boot/efi
mount "${DEVICE}1" /mnt/boot/efi
rsync -a / /mnt --exclude=/proc --exclude=/sys --exclude=/dev --exclude=/run
grub-install --target=x86_64-efi --efi-directory=/mnt/boot/efi --boot-directory=/mnt/boot "$DEVICE"
grub-install --target=i386-pc --boot-directory=/mnt/boot "$DEVICE"
chroot /mnt update-grub

# === Autologin: bỏ màn hình nhập mật khẩu LightDM ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /mnt/etc/lightdm
cp "$SCRIPT_DIR/../configs/lightdm.conf" /mnt/etc/lightdm/lightdm.conf
echo "[OK] LightDM autologin configured → user: mixtralr"

umount -R /mnt
