#!/usr/bin/env python3
"""
MXL Runner - Runtime thực thi file .mxl của MixtralOS
Hỗ trợ 3 chế độ: gui | terminal | silent
"""
import sys, os, json, zipfile, shutil, tempfile, subprocess, argparse

# ─── PATH RESOLVER ────────────────────────────────────────────────
HOME = os.path.expanduser("~")

def resolve_path(p: str) -> str:
    """Chuyển đổi path tùy biến → path thực trên hệ thống."""
    replacements = {
        "{desktop}":   os.path.join(HOME, "Desktop"),
        "{documents}": os.path.join(HOME, "Documents"),
        "{pictures}":  os.path.join(HOME, "Pictures"),
        "{downloads}": os.path.join(HOME, "Downloads"),
        "{music}":     os.path.join(HOME, "Music"),
        "{videos}":    os.path.join(HOME, "Videos"),
        "{home}":      HOME,
        "{tmp}":       tempfile.gettempdir(),
        # Ổ đĩa kiểu Windows
        "{C}":         "/",
        "{D}":         "/media/mixtralr/D",
        "{E}":         "/media/mixtralr/E",
        "{F}":         "/media/mixtralr/F",
        # Thư mục hệ thống
        "{apps}":      "/usr/share/mixtralr/apps",
        "{bin}":       "/usr/local/bin",
    }
    for key, val in replacements.items():
        p = p.replace(key, val)
    return os.path.expanduser(p)


# ─── TERMINAL UI ──────────────────────────────────────────────────
def run_terminal(mxl_path: str, manifest: dict, extract_dir: str):
    """Chạy chế độ terminal (giống cmd)."""
    name    = manifest.get("name", "MXL Package")
    version = manifest.get("version", "1.0")
    author  = manifest.get("author", "Unknown")
    desc    = manifest.get("description", "")

    print(f"\n{'='*50}")
    print(f"  {name}  v{version}  by {author}")
    if desc:
        print(f"  {desc}")
    print(f"{'='*50}")

    # Install files
    rules = manifest.get("install_rules", [])
    if rules:
        print(f"\n[*] Cài đặt {len(rules)} file(s)...")
        for rule in rules:
            src  = os.path.join(extract_dir, rule["src"])
            dest = resolve_path(rule["dest"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            # chmod nếu cần
            if rule.get("executable", False):
                os.chmod(dest, 0o755)
            print(f"    ✓ {rule['src']} → {dest}")

    # Chạy entry point
    entry = manifest.get("entry")
    if entry:
        entry_path = os.path.join(extract_dir, entry)
        entry_type = manifest.get("entry_type", "bash")
        env = build_env(extract_dir, manifest)
        print(f"\n[*] Chạy: {entry} ({entry_type})")
        print("-" * 50)
        if entry_type == "python":
            subprocess.run([sys.executable, entry_path], env=env)
        elif entry_type == "bash":
            os.chmod(entry_path, 0o755)
            subprocess.run(["/bin/bash", entry_path], env=env)
        elif entry_type == "binary":
            os.chmod(entry_path, 0o755)
            subprocess.run([entry_path], env=env)
        print("-" * 50)

    print(f"\n[✓] Hoàn tất: {name}\n")


# ─── GUI UI ───────────────────────────────────────────────────────
def run_gui(mxl_path: str, manifest: dict, extract_dir: str):
    """Chạy chế độ GUI (cửa sổ PyQt6)."""
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QTextEdit, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont, QColor

    app = QApplication.instance() or QApplication(sys.argv)

    name    = manifest.get("name", "MXL Package")
    version = manifest.get("version", "1.0")
    author  = manifest.get("author", "Unknown")
    desc    = manifest.get("description", "")
    w_size  = manifest.get("window_size", [520, 400])
    w_title = manifest.get("window_title", f"Cài đặt - {name}")
    theme   = manifest.get("theme", "dark")

    # ── Worker thread ──
    class Worker(QThread):
        log    = pyqtSignal(str)
        prog   = pyqtSignal(int)
        done   = pyqtSignal(bool)

        def run(self):
            try:
                rules = manifest.get("install_rules", [])
                total = len(rules) + 1
                step  = 0

                for rule in rules:
                    src  = os.path.join(extract_dir, rule["src"])
                    dest = resolve_path(rule["dest"])
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)
                    if rule.get("executable", False):
                        os.chmod(dest, 0o755)
                    step += 1
                    self.log.emit(f"✓ {rule['src']} → {dest}")
                    self.prog.emit(int(step / total * 80))

                entry = manifest.get("entry")
                if entry:
                    entry_path = os.path.join(extract_dir, entry)
                    entry_type = manifest.get("entry_type", "bash")
                    env = build_env(extract_dir, manifest)
                    self.log.emit(f"\n▶ Chạy: {entry}")
                    if entry_type == "python":
                        r = subprocess.run([sys.executable, entry_path],
                                           env=env, capture_output=True, text=True)
                    elif entry_type == "bash":
                        os.chmod(entry_path, 0o755)
                        r = subprocess.run(["/bin/bash", entry_path],
                                           env=env, capture_output=True, text=True)
                    elif entry_type == "binary":
                        os.chmod(entry_path, 0o755)
                        r = subprocess.run([entry_path],
                                           env=env, capture_output=True, text=True)
                    else:
                        r = None
                    if r and r.stdout:
                        self.log.emit(r.stdout)
                    if r and r.stderr:
                        self.log.emit(f"[stderr] {r.stderr}")

                self.prog.emit(100)
                self.done.emit(True)
            except Exception as e:
                self.log.emit(f"\n[LỖI] {e}")
                self.done.emit(False)

    # ── Window ──
    win = QWidget()
    win.setWindowTitle(w_title)
    win.resize(w_size[0], w_size[1])
    win.setWindowFlags(Qt.WindowType.Window)

    if theme == "dark":
        win.setStyleSheet("""
            QWidget { background: #0d1117; color: #e6edf3; font-family: 'DejaVu Sans'; }
            QLabel  { color: #e6edf3; }
            QTextEdit { background: #161b22; color: #7ee787; border: 1px solid #30363d;
                        font-family: monospace; font-size: 11px; border-radius: 6px; padding: 6px; }
            QPushButton { background: #238636; color: #fff; border: none;
                          border-radius: 6px; padding: 8px 20px; font-size: 13px; }
            QPushButton:hover   { background: #2ea043; }
            QPushButton:disabled{ background: #21262d; color: #484f58; }
            QProgressBar { background: #21262d; border: none; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background: #238636; border-radius: 4px; }
        """)
    else:
        win.setStyleSheet("""
            QWidget { background: #f6f8fa; color: #24292f; font-family: 'DejaVu Sans'; }
            QLabel  { color: #24292f; }
            QTextEdit { background: #ffffff; color: #1f2328; border: 1px solid #d0d7de;
                        font-family: monospace; font-size: 11px; border-radius: 6px; padding: 6px; }
            QPushButton { background: #1f883d; color: #fff; border: none;
                          border-radius: 6px; padding: 8px 20px; font-size: 13px; }
            QPushButton:hover   { background: #1a7f37; }
            QPushButton:disabled{ background: #eaeef2; color: #8c959f; }
            QProgressBar { background: #eaeef2; border: none; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background: #1f883d; border-radius: 4px; }
        """)

    layout = QVBoxLayout(win)
    layout.setSpacing(12)
    layout.setContentsMargins(20, 20, 20, 20)

    # Header
    lbl_name = QLabel(f"⚡ {name}  <span style='color:#8b949e;font-size:12px;'>v{version}</span>")
    lbl_name.setFont(QFont("DejaVu Sans", 16, QFont.Weight.Bold))
    lbl_name.setTextFormat(Qt.TextFormat.RichText)
    layout.addWidget(lbl_name)

    if desc:
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

    lbl_author = QLabel(f"Tác giả: {author}")
    lbl_author.setStyleSheet("color: #8b949e; font-size: 11px;")
    layout.addWidget(lbl_author)

    # Divider
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #30363d;")
    layout.addWidget(line)

    # Log
    log_box = QTextEdit()
    log_box.setReadOnly(True)
    log_box.setPlaceholderText("Nhật ký cài đặt sẽ hiện ở đây...")
    layout.addWidget(log_box, 1)

    # Progress bar
    pbar = QProgressBar()
    pbar.setValue(0)
    layout.addWidget(pbar)

    # Buttons
    btn_row = QHBoxLayout()
    btn_install = QPushButton("▶  Cài đặt")
    btn_close   = QPushButton("✕  Đóng")
    btn_close.setStyleSheet("""
        QPushButton { background: #21262d; color: #e6edf3; border: none;
                      border-radius: 6px; padding: 8px 20px; font-size: 13px; }
        QPushButton:hover { background: #30363d; }
    """)
    btn_row.addStretch()
    btn_row.addWidget(btn_close)
    btn_row.addWidget(btn_install)
    layout.addLayout(btn_row)

    worker = Worker()

    def append_log(msg):
        log_box.append(msg)

    def on_done(success):
        pbar.setValue(100)
        btn_install.setEnabled(False)
        if success:
            log_box.append("\n✅ Cài đặt thành công!")
            btn_close.setText("✓  Đóng")
        else:
            log_box.append("\n❌ Cài đặt thất bại!")
            btn_close.setText("✕  Thoát")

    def start_install():
        btn_install.setEnabled(False)
        log_box.clear()
        log_box.append(f"[*] Bắt đầu cài đặt {name}...\n")
        worker.start()

    worker.log.connect(append_log)
    worker.prog.connect(pbar.setValue)
    worker.done.connect(on_done)
    btn_install.clicked.connect(start_install)
    btn_close.clicked.connect(win.close)

    win.show()
    sys.exit(app.exec())


# ─── SILENT MODE ──────────────────────────────────────────────────
def run_silent(mxl_path: str, manifest: dict, extract_dir: str):
    """Chạy không hiển thị gì (background)."""
    rules = manifest.get("install_rules", [])
    for rule in rules:
        src  = os.path.join(extract_dir, rule["src"])
        dest = resolve_path(rule["dest"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        if rule.get("executable", False):
            os.chmod(dest, 0o755)

    entry = manifest.get("entry")
    if entry:
        entry_path = os.path.join(extract_dir, entry)
        entry_type = manifest.get("entry_type", "bash")
        env = build_env(extract_dir, manifest)
        if entry_type == "python":
            subprocess.run([sys.executable, entry_path], env=env)
        elif entry_type == "bash":
            os.chmod(entry_path, 0o755)
            subprocess.run(["/bin/bash", entry_path], env=env)
        elif entry_type == "binary":
            os.chmod(entry_path, 0o755)
            subprocess.run([entry_path], env=env)


# ─── HELPERS ──────────────────────────────────────────────────────
def build_env(extract_dir: str, manifest: dict) -> dict:
    env = os.environ.copy()
    env["MXL_EXTRACT_DIR"] = extract_dir
    env["MXL_HOME"]        = HOME
    env["MXL_DESKTOP"]     = os.path.join(HOME, "Desktop")
    env["MXL_DOCUMENTS"]   = os.path.join(HOME, "Documents")
    env["MXL_PICTURES"]    = os.path.join(HOME, "Pictures")
    env["MXL_DOWNLOADS"]   = os.path.join(HOME, "Downloads")
    env["MXL_NAME"]        = manifest.get("name", "")
    env["MXL_VERSION"]     = manifest.get("version", "1.0")
    return env


# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MXL Runner - MixtralOS Package Runner")
    parser.add_argument("mxl_file", help="Đường dẫn tới file .mxl")
    parser.add_argument("--mode", choices=["gui","terminal","silent"],
                        help="Ghi đè chế độ chạy từ manifest")
    args = parser.parse_args()

    mxl_path = os.path.abspath(args.mxl_file)
    if not os.path.isfile(mxl_path):
        print(f"[LỖI] Không tìm thấy file: {mxl_path}")
        sys.exit(1)

    if not zipfile.is_zipfile(mxl_path):
        print("[LỖI] File .mxl không hợp lệ (phải là ZIP archive).")
        sys.exit(1)

    extract_dir = tempfile.mkdtemp(prefix="mxl_")
    try:
        with zipfile.ZipFile(mxl_path, "r") as zf:
            zf.extractall(extract_dir)

        manifest_path = os.path.join(extract_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            print("[LỖI] Thiếu manifest.json trong file .mxl")
            sys.exit(1)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        mode = args.mode or manifest.get("ui", "gui")

        # Tạo thư mục đích trước
        for folder in [
            os.path.join(HOME, "Desktop"),
            os.path.join(HOME, "Documents"),
            os.path.join(HOME, "Pictures"),
            os.path.join(HOME, "Downloads"),
        ]:
            os.makedirs(folder, exist_ok=True)

        if mode == "terminal":
            run_terminal(mxl_path, manifest, extract_dir)
        elif mode == "silent":
            run_silent(mxl_path, manifest, extract_dir)
        else:
            run_gui(mxl_path, manifest, extract_dir)

    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
