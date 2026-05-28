# 🖥️ MixtralOS

> Hệ điều hành Linux tùy chỉnh dựa trên Debian 12 Bookworm, với desktop environment viết hoàn toàn bằng Python + PyQt6.

![Build Status](https://github.com/aanhh279/MixtralrOS/actions/workflows/build-iso.yml/badge.svg)
![GitHub Release](https://img.shields.io/github/v/release/aanhh279/MixtralrOS)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Tính năng

- 🖥️ **Custom Desktop (PyQt6)** — Toàn bộ giao diện viết từ đầu: taskbar, launcher, splash screen, action center, settings
- 📜 **MXL Script Engine** — Ngôn ngữ script riêng với `mxl-run` và `mxl-builder`
- 🎮 **Tương thích VGA rộng** — Chạy tốt trong VirtualBox, VMware và máy thật
- 🌐 **NetworkManager** — Kết nối WiFi/LAN tự động ngay khi boot
- 💿 **Live Boot** — Chạy thẳng từ USB, không cần cài đặt
- ⚡ **BIOS + UEFI** — ISO hybrid, hỗ trợ cả máy cũ lẫn máy mới

---

## 📥 Tải về

Vào trang **[Releases](https://github.com/aanhh279/MixtralrOS/releases)** để tải file `Mixtralr.iso` mới nhất.

---

## 🚀 Cách dùng

### Ghi vào USB

| Hệ điều hành | Cách ghi |
|---|---|
| Windows | [Rufus](https://rufus.ie) → chọn ISO → chọn USB → Start |
| Linux | `sudo dd if=Mixtralr.iso of=/dev/sdX bs=4M status=progress` |
| macOS | [balenaEtcher](https://etcher.balena.io) |

### Đăng nhập khẩn cấp & thực nghiệm

```
Username: mixtralr
Password: mixtralr
```

### Boot options

| Tùy chọn | Mô tả |
|---|---|
| **MixtralOS** | Mặc định, nomodeset — an toàn cho VM |
| **MixtralOS (KMS)** | GPU native, dành cho máy thật Intel/AMD |
| **MixtralOS (Safe Mode)** | 800×600 VESA, khi gặp lỗi màn hình |
| **MixtralOS (Recovery Shell)** | Debug, vào thẳng shell |

---

## 🔧 Thông số kỹ thuật

| Thành phần | Chi tiết |
|---|---|
| Base | Debian 12 Bookworm |
| Architecture | x86_64 (amd64) |
| Desktop | PyQt6 Custom |
| Display Server | Xorg + Openbox |
| Kernel | linux-image-amd64 |
| Login | Auto-login TTY1 |

---

## 🏗️ Build từ source

Yêu cầu: Ubuntu/Debian với `sudo`.

```bash
git clone https://github.com/aanhh279/MixtralrOS.git
cd MixtralrOS
sudo bash build/build.sh
```

ISO sẽ xuất ra `fileOS/Mixtralr.iso`. Quá trình build mất khoảng 30–50 phút.

### Build tự động (GitHub Actions)

Mỗi lần push lên `main`, GitHub Actions sẽ tự động build ISO và upload lên Releases.

---

## 📁 Cấu trúc project

```
MixtralrOS/
├── build/          # Script build ISO
├── boot/           # GRUB config, Plymouth theme
├── desktop/        # Toàn bộ source code desktop (PyQt6)
│   ├── desktop.py      # Desktop environment chính
│   ├── taskbar.py      # Thanh taskbar
│   ├── launcher.py     # App launcher
│   ├── splash.py       # Splash screen
│   ├── settings.py     # Cài đặt hệ thống
│   └── ...
├── mxl/            # MXL script engine
├── scripts/        # Scripts cài đặt và khởi động
├── configs/        # Config LightDM, desktop session
├── themes/         # QSS theme (neon)
└── picture/        # Wallpaper mặc định
```

---

## 📄 License

MIT License — tự do sử dụng, chỉnh sửa và phân phối.
