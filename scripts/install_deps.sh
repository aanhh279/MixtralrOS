#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  debootstrap live-build xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
  squashfs-tools rsync wget curl ca-certificates \
  python3 python3-pyqt6 python3-psutil python3-watchdog \
  xserver-xorg xinit openbox lightdm lightdm-gtk-greeter \
  plymouth plymouth-themes \
  systemd-sysv network-manager sudo vim git
