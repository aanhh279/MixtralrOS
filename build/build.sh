#!/usr/bin/env bash
set -euo pipefail

# =================================================================
# MIXTRALOS ISO BUILDER – Fixed edition
# Hỗ trợ: VirtualBox / VMware / BIOS / UEFI / mọi VGA
# =================================================================

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="/tmp/mixtralros-build"
CHROOT="$WORK/chroot"
IMAGE="$WORK/image"
ISO_OUT="$ROOT/fileOS/Mixtralr.iso"
mkdir -p "$ROOT/fileOS"

DISTRO="bookworm"
ARCH="amd64"

echo "[*] ROOT    = $ROOT"
echo "[*] WORK    = $WORK"
echo "[*] ISO OUT = $ISO_OUT"

# ── Helper: mount/umount chroot filesystems ────────────────────────
chroot_mount() {
    sudo mount --bind /proc  "$CHROOT/proc"
    sudo mount --bind /sys   "$CHROOT/sys"
    sudo mount --bind /dev   "$CHROOT/dev"
    sudo mount --bind /dev/pts "$CHROOT/dev/pts"
}

chroot_umount() {
    sudo umount "$CHROOT/dev/pts" 2>/dev/null || true
    sudo umount "$CHROOT/dev"     2>/dev/null || true
    sudo umount "$CHROOT/sys"     2>/dev/null || true
    sudo umount "$CHROOT/proc"    2>/dev/null || true
}

# Đảm bảo umount dù build fail
trap chroot_umount EXIT

# ── Clean ─────────────────────────────────────────────────────────
sudo rm -rf "$WORK"
mkdir -p "$WORK" "$CHROOT" "$IMAGE"

# ── Dependencies (host) ────────────────────────────────────────────
# FIX #7: bỏ isolinux vì grub-mkrescue đảm nhiệm hết BIOS+UEFI
# FIX: bỏ python3/pyqt6/psutil khỏi host – chúng chỉ cần trong chroot
echo "[*] Installing build deps..."
sudo apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update -qq
sudo apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false install -y \
    debootstrap squashfs-tools xorriso \
    grub-pc-bin grub-efi-amd64-bin grub-common \
    mtools dosfstools rsync

# ── Fix CRLF ──────────────────────────────────────────────────────
echo "[*] Fixing CRLF..."
find "$ROOT" -type f \( -name "*.py" -o -name "*.sh" \) \
    -exec sed -i 's/\r$//' {} \; 2>/dev/null || true

# ── Rename typo ───────────────────────────────────────────────────
[ -f "$ROOT/scripts/mixtralr-autostart.servie" ] && \
mv "$ROOT/scripts/mixtralr-autostart.servie" \
   "$ROOT/scripts/mixtralr-autostart.service" || true
# FIX #4: thêm sudo để chmod không fail với file owned by root
sudo chmod +x "$ROOT/scripts/"* 2>/dev/null || true

# ── Debootstrap ───────────────────────────────────────────────────
echo "[*] Creating Debian rootfs (bookworm)..."
sudo debootstrap \
    --arch="$ARCH" \
    "$DISTRO" \
    "$CHROOT" \
    http://deb.debian.org/debian

sudo cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"

# FIX #1: Mount /proc /sys /dev trước khi chroot
mkdir -p "$CHROOT/proc" "$CHROOT/sys" "$CHROOT/dev" "$CHROOT/dev/pts"
chroot_mount

# ── Chroot setup script ───────────────────────────────────────────
sudo tee "$CHROOT/setup.sh" > /dev/null << 'EOF'
#!/usr/bin/env bash
set -e

# FIX #3: thêm flag bypass date check cho cả install
APT="apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false"
export DEBIAN_FRONTEND=noninteractive

$APT update -qq

# Cài đầy đủ drivers VGA để không bị màn hình đen
# FIX #2: bỏ libgles2-mesa (không tồn tại trong bookworm, đã có libgles2 bên dưới)
$APT install -y \
    linux-image-amd64 live-boot systemd-sysv \
    sudo locales \
    xserver-xorg xinit \
    xserver-xorg-video-vesa \
    xserver-xorg-video-fbdev \
    xserver-xorg-video-all \
    xserver-xorg-video-dummy \
    mesa-utils libgl1-mesa-dri \
    libgles2 libegl1 \
    openbox \
    dbus-x11 xterm \
    x11-xserver-utils \
    network-manager network-manager-gnome \
    python3 python3-pyqt6 \
    python3-psutil \
    plymouth plymouth-themes \
    fonts-dejavu fonts-noto-color-emoji \
    ca-certificates curl wget nano \
    xdg-utils xdotool wmctrl \
    pciutils usbutils

# Locale
sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
locale-gen
export LANG=en_US.UTF-8

# User
useradd -m -s /bin/bash mixtralr 2>/dev/null || true
echo "mixtralr:mixtralr" | chpasswd
echo 'mixtralr ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/mixtralr
chmod 0440 /etc/sudoers.d/mixtralr

# NetworkManager – /proc đã được mount nên systemctl hoạt động đúng
systemctl enable NetworkManager 2>/dev/null || true

# ── Autologin TTY1 ────────────────────────────────────────────────
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << CONF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin mixtralr --noclear %I \$TERM
CONF

# ── Auto-start X khi login TTY1 ──────────────────────────────────
cat > /home/mixtralr/.bash_profile << PROF
export LANG=en_US.UTF-8
if [ -z "\$DISPLAY" ] && [ "\$(tty)" = "/dev/tty1" ]; then
    exec startx /usr/bin/start-mixtralr-session -- :0 vt1 \
        -keeptty -novtswitch 2>/tmp/x-error.log
fi
PROF
chown mixtralr:mixtralr /home/mixtralr/.bash_profile

# ── Xorg config: KHÔNG tạo xorg.conf, để Xorg tự detect ─────────
# Lý do: nomodeset trong GRUB tắt KMS, nhưng Driver "modesetting" cần KMS
# → conflict → Xorg crash "no screens found"
# Để trống → Xorg tự chọn vesa/fbdev khi nomodeset, hoặc modesetting khi KMS on
rm -f /etc/X11/xorg.conf

# Script wrapper để fallback driver nếu cần
cat > /usr/bin/start-mixtralr-session << 'SESS'
#!/usr/bin/env bash
export DISPLAY="${DISPLAY:-:0}"
export QT_QPA_PLATFORM=xcb
export XDG_CURRENT_DESKTOP=Mixtralr
export QT_SCALE_FACTOR=1
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export LANG=en_US.UTF-8

UID_VAL="$(id -u)"
export XDG_RUNTIME_DIR="/run/user/${UID_VAL}"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# Chờ X sẵn sàng tối đa 30s
for i in $(seq 1 30); do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break
    sleep 1
done

# FIX #5: chỉ chạy xsetroot khi X thực sự sẵn sàng
if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    xsetroot -solid '#080b14' 2>/dev/null || true
else
    export QT_QPA_PLATFORM=offscreen
fi

# nm-applet needs dbus - started alongside splash after dbus-launch
exec dbus-launch --exit-with-session \
    bash -c 'nm-applet 2>/dev/null & python3 /usr/share/mixtralr/desktop/splash.py'
SESS
chmod 0755 /usr/bin/start-mixtralr-session

mkdir -p /usr/share/mixtralr/desktop /usr/local/bin

# Hostname
echo "mixtralros" > /etc/hostname
echo "127.0.1.1 mixtralros" >> /etc/hosts

# Quiet boot
echo ""       > /etc/motd
touch /etc/legal; chmod 000 /etc/legal
echo "MixtralOS" > /etc/issue
echo "MixtralOS" > /etc/issue.net

EOF

sudo chmod +x "$CHROOT/setup.sh"
sudo chroot "$CHROOT" /bin/bash /setup.sh
sudo rm -f "$CHROOT/setup.sh"

# ── Copy desktop files ────────────────────────────────────────────
echo "[*] Copying desktop files..."
sudo mkdir -p "$CHROOT/usr/share/mixtralr/desktop"
# FIX #6: rsync đã copy toàn bộ desktop/ kể cả các module mới → bỏ loop thừa
sudo rsync -a "$ROOT/desktop/" "$CHROOT/usr/share/mixtralr/desktop/"
sudo chmod +x \
    "$CHROOT/usr/share/mixtralr/desktop/desktop.py" \
    "$CHROOT/usr/share/mixtralr/desktop/splash.py" 2>/dev/null || true

# ── Copy picture (wallpapers) ────────────────────────────────────
echo "[*] Copying default wallpaper..."
sudo mkdir -p "$CHROOT/usr/share/mixtralr/picture"
if [ -d "$ROOT/picture" ]; then
    sudo rsync -a "$ROOT/picture/" "$CHROOT/usr/share/mixtralr/picture/"
else
    echo "[!] Thư mục picture/ không tồn tại, bỏ qua."
fi

# Bảo vệ ảnh mặc định
DEFAULT_WP="$CHROOT/usr/share/mixtralr/picture/mixtralr-ui-d.png"
if [ -f "$DEFAULT_WP" ]; then
    sudo chown root:root "$DEFAULT_WP"
    sudo chmod 0444 "$DEFAULT_WP"
    echo "[✓] mixtralr-ui-d.png → protected (0444, root:root)"
else
    echo "[!] mixtralr-ui-d.png không tìm thấy trong picture/ – cần thêm file ảnh!"
fi

# ── Plymouth theme ────────────────────────────────────────────────
echo "[*] Installing Plymouth theme..."
sudo mkdir -p "$CHROOT/usr/share/plymouth/themes/mixtralr"
sudo cp "$ROOT/boot/plymouth-mixtralr.plymouth" \
    "$CHROOT/usr/share/plymouth/themes/mixtralr/mixtralr.plymouth"
sudo cp "$ROOT/boot/mixtralr.script" \
    "$CHROOT/usr/share/plymouth/themes/mixtralr/mixtralr.script"

sudo tee "$CHROOT/setup-plymouth.sh" > /dev/null << 'EOF'
#!/bin/bash
set -e
plymouth-set-default-theme -R mixtralr 2>/dev/null || \
    update-alternatives --install \
        /usr/share/plymouth/themes/default.plymouth \
        default.plymouth \
        /usr/share/plymouth/themes/mixtralr/mixtralr.plymouth 100
mkdir -p /etc/sysctl.d
echo "kernel.printk = 3 4 1 3" > /etc/sysctl.d/99-quiet-boot.conf
EOF
sudo chmod +x "$CHROOT/setup-plymouth.sh"
sudo chroot "$CHROOT" /bin/bash /setup-plymouth.sh
sudo rm -f "$CHROOT/setup-plymouth.sh"

# ── Initramfs ─────────────────────────────────────────────────────
echo "[*] Updating initramfs..."
sudo chroot "$CHROOT" update-initramfs -u

# ── MXL system ────────────────────────────────────────────────────
echo "[*] Installing MXL system..."
sudo mkdir -p "$CHROOT/usr/share/mixtralr/mxl"
sudo cp "$ROOT/mxl/mxl_runner.py"  "$CHROOT/usr/share/mixtralr/mxl/"
sudo cp "$ROOT/mxl/mxl_builder.py" "$CHROOT/usr/share/mixtralr/mxl/"

sudo tee "$CHROOT/usr/local/bin/mxl-run" > /dev/null << 'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/mixtralr/mxl/mxl_runner.py "$@"
EOF
sudo chmod 0755 "$CHROOT/usr/local/bin/mxl-run"

sudo tee "$CHROOT/usr/local/bin/mxl-builder" > /dev/null << 'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/mixtralr/mxl/mxl_builder.py "$@"
EOF
sudo chmod 0755 "$CHROOT/usr/local/bin/mxl-builder"

# FIX #1: Umount trước khi đóng squashfs
chroot_umount
trap - EXIT

# ── SquashFS ──────────────────────────────────────────────────────
echo "[*] Creating squashfs..."
mkdir -p "$IMAGE/live"
sudo mksquashfs \
    "$CHROOT" \
    "$IMAGE/live/filesystem.squashfs" \
    -comp xz -e boot

# ── Kernel ────────────────────────────────────────────────────────
echo "[*] Copying kernel..."
KERNEL=$(find "$CHROOT/boot" -name "vmlinuz-*" | sort -V | tail -n1)
INITRD=$(find "$CHROOT/boot" -name "initrd.img-*" | sort -V | tail -n1)

[ -n "$KERNEL" ] && [ -f "$KERNEL" ] || { echo "[!] Kernel missing!"; exit 1; }
[ -n "$INITRD" ] && [ -f "$INITRD" ] || { echo "[!] Initrd missing!"; exit 1; }

sudo cp "$KERNEL" "$IMAGE/vmlinuz"
sudo cp "$INITRD" "$IMAGE/initrd"

# ── GRUB config – hỗ trợ BIOS + UEFI + mọi VGA ──────────────────
echo "[*] Creating GRUB config..."
mkdir -p "$IMAGE/boot/grub"

cat > "$IMAGE/boot/grub/grub.cfg" << 'EOF'
# MixtralOS GRUB config – Universal (BIOS+UEFI, all VGA)
set timeout=5
set default=0
set gfxpayload=keep

set menu_color_normal=black/black
set menu_color_highlight=white/black
terminal_output console

menuentry "MixtralOS" {
    linux /vmlinuz boot=live \
          quiet splash loglevel=0 \
          nomodeset \
          vga=788 \
          video=800x600 \
          rd.systemd.show_status=false \
          rd.udev.log_level=0 \
          vt.global_cursor_default=0 \
          plymouth.ignore-serial-consoles \
          fsck.mode=skip \
          net.ifnames=0 biosdevname=0
    initrd /initrd
}

menuentry "MixtralOS (KMS – Intel/AMD GPU)" {
    linux /vmlinuz boot=live \
          quiet splash loglevel=0 \
          rd.systemd.show_status=false \
          vt.global_cursor_default=0 \
          fsck.mode=skip
    initrd /initrd
}

menuentry "MixtralOS (Safe Mode – 800x600)" {
    linux /vmlinuz boot=live nomodeset vga=788 video=800x600 loglevel=3
    initrd /initrd
}

menuentry "MixtralOS (Recovery Shell)" {
    linux /vmlinuz boot=live nomodeset loglevel=3 systemd.unit=rescue.target
    initrd /initrd
}
EOF

# ── Build ISO (BIOS + UEFI hybrid) ───────────────────────────────
echo "[*] Building ISO (BIOS + UEFI hybrid)..."

sudo grub-mkrescue \
    --modules="part_gpt part_msdos fat ext2 normal boot linux echo all_video gfxterm" \
    -o "$ISO_OUT" \
    "$IMAGE" \
    2>&1

echo ""
echo "====================================="
echo " BUILD thành công – MixtralOS"
echo "====================================="
echo " ISO: $ISO_OUT"
echo " Size: $(du -sh "$ISO_OUT" 2>/dev/null | cut -f1)"
echo ""
echo " Boot options:"
echo "   MixtralOS           → nomodeset (an toàn cho VM)"
echo "   KMS entry           → native GPU (máy thật)"
echo "   Safe Mode           → 800x600 VESA"
echo "   Recovery Shell      → debug"
echo ""
