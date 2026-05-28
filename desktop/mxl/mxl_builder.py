#!/usr/bin/env python3
"""
MXL Builder - Công cụ tạo file .mxl cho MixtralOS
Dùng: python3 mxl_builder.py [--gui]  hoặc  mxl-builder --gui
"""
import sys, os, json, zipfile, argparse

# ─── MANIFEST TEMPLATE ────────────────────────────────────────────
MANIFEST_TEMPLATE = {
    "name":        "My App",
    "version":     "1.0",
    "author":      "Your Name",
    "description": "Mô tả ứng dụng của bạn",

    # gui | terminal | silent
    "ui": "gui",

    # Tiêu đề & kích thước cửa sổ cài đặt (chỉ dùng khi ui=gui)
    "window_title": "Cài đặt - My App",
    "window_size":  [520, 420],

    # Màu theme: dark | light
    "theme": "dark",

    # Loại entry point: python | bash | binary
    "entry_type": "bash",

    # File chạy sau khi cài (relative path trong zip)
    "entry": "main.sh",

    # Danh sách file cài vào hệ thống
    # dest hỗ trợ: {desktop} {documents} {pictures} {downloads}
    #              {music} {videos} {home} {tmp}
    #              {C} {D} {E} (ổ đĩa)
    #              {apps} {bin}
    "install_rules": [
        {
            "src":        "files/myapp.py",
            "dest":       "{desktop}/myapp.py",
            "executable": False
        },
        {
            "src":        "files/run.sh",
            "dest":       "{bin}/myapp",
            "executable": True
        }
    ]
}


# ─── TERMINAL BUILDER ─────────────────────────────────────────────
def build_terminal(output: str, source_dir: str):
    """Build từ thư mục source (phải có manifest.json + các file)."""
    manifest_path = os.path.join(source_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        # Tạo manifest mẫu
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(MANIFEST_TEMPLATE, f, ensure_ascii=False, indent=2)
        print(f"[*] Đã tạo manifest.json mẫu tại: {manifest_path}")
        print(f"    Hãy sửa lại rồi chạy lại lệnh này.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    name = manifest.get("name", "package")
    if not output:
        output = f"{name.lower().replace(' ', '_')}.mxl"

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            # Bỏ qua thư mục ẩn
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                filepath = os.path.join(root, file)
                arcname  = os.path.relpath(filepath, source_dir)
                zf.write(filepath, arcname)

    size = os.path.getsize(output)
    print(f"\n✓ Build thành công!")
    print(f"  File : {output}")
    print(f"  Size : {size/1024:.1f} KB")
    print(f"  App  : {name}  v{manifest.get('version','1.0')}")


# ─── GUI BUILDER ──────────────────────────────────────────────────
def build_gui():
    """Giao diện đồ họa để tạo file .mxl."""
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
        QFileDialog, QGroupBox, QListWidget, QListWidgetItem,
        QMessageBox, QSpinBox, QCheckBox, QTabWidget, QFrame
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont

    app = QApplication.instance() or QApplication(sys.argv)

    win = QWidget()
    win.setWindowTitle("MXL Builder - Tạo gói .mxl")
    win.resize(700, 620)
    win.setStyleSheet("""
        QWidget      { background: #0d1117; color: #e6edf3; font-family: 'DejaVu Sans'; font-size: 13px; }
        QGroupBox    { border: 1px solid #30363d; border-radius: 8px; margin-top: 8px;
                       padding: 10px; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; color: #58a6ff; }
        QLineEdit, QTextEdit, QComboBox {
            background: #161b22; border: 1px solid #30363d; border-radius: 6px;
            padding: 5px 8px; color: #e6edf3; }
        QLineEdit:focus, QTextEdit:focus { border-color: #58a6ff; }
        QPushButton  { background: #21262d; color: #e6edf3; border: none;
                       border-radius: 6px; padding: 7px 16px; }
        QPushButton:hover { background: #30363d; }
        QPushButton#btnBuild { background: #238636; font-size: 14px; padding: 9px 24px; }
        QPushButton#btnBuild:hover { background: #2ea043; }
        QPushButton#btnAdd   { background: #1f6feb; }
        QPushButton#btnAdd:hover { background: #388bfd; }
        QListWidget  { background: #161b22; border: 1px solid #30363d;
                       border-radius: 6px; padding: 4px; }
        QTabWidget::pane { border: 1px solid #30363d; border-radius: 6px; }
        QTabBar::tab { background: #161b22; color: #8b949e; padding: 8px 18px;
                       border-radius: 4px 4px 0 0; margin-right: 2px; }
        QTabBar::tab:selected { background: #21262d; color: #e6edf3; }
        QSpinBox     { background: #161b22; border: 1px solid #30363d;
                       border-radius: 6px; padding: 5px; }
    """)

    main_layout = QVBoxLayout(win)
    main_layout.setSpacing(12)
    main_layout.setContentsMargins(16, 16, 16, 16)

    # Title
    title = QLabel("⚙  MXL Builder")
    title.setFont(QFont("DejaVu Sans", 18, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff;")
    main_layout.addWidget(title)

    tabs = QTabWidget()
    main_layout.addWidget(tabs, 1)

    # ── Tab 1: Thông tin ──────────────────────────────────────────
    tab_info = QWidget()
    t1 = QVBoxLayout(tab_info)
    t1.setSpacing(10)

    grp_meta = QGroupBox("Thông tin gói")
    g1 = QGridLayout(grp_meta)
    g1.setSpacing(8)

    fields = {}
    rows = [
        ("Tên ứng dụng *", "name",    "My App"),
        ("Phiên bản *",    "version", "1.0"),
        ("Tác giả",        "author",  "Your Name"),
        ("Mô tả",          "desc",    ""),
    ]
    for i, (label, key, default) in enumerate(rows):
        g1.addWidget(QLabel(label), i, 0)
        le = QLineEdit(default)
        fields[key] = le
        g1.addWidget(le, i, 1)

    t1.addWidget(grp_meta)

    grp_ui = QGroupBox("Giao diện & Chạy")
    g2 = QGridLayout(grp_ui)
    g2.setSpacing(8)

    g2.addWidget(QLabel("Chế độ UI"), 0, 0)
    cmb_ui = QComboBox()
    cmb_ui.addItems(["gui", "terminal", "silent"])
    g2.addWidget(cmb_ui, 0, 1)

    g2.addWidget(QLabel("Theme (gui)"), 1, 0)
    cmb_theme = QComboBox()
    cmb_theme.addItems(["dark", "light"])
    g2.addWidget(cmb_theme, 1, 1)

    g2.addWidget(QLabel("Tiêu đề cửa sổ"), 2, 0)
    le_title = QLineEdit("Cài đặt - My App")
    fields["window_title"] = le_title
    g2.addWidget(le_title, 2, 1)

    g2.addWidget(QLabel("Kích thước (W x H)"), 3, 0)
    sz_row = QHBoxLayout()
    sb_w = QSpinBox(); sb_w.setRange(300,1920); sb_w.setValue(520)
    sb_h = QSpinBox(); sb_h.setRange(200,1080); sb_h.setValue(420)
    sz_row.addWidget(sb_w); sz_row.addWidget(QLabel("×")); sz_row.addWidget(sb_h)
    g2.addLayout(sz_row, 3, 1)

    t1.addWidget(grp_ui)

    grp_entry = QGroupBox("Entry Point (file chạy sau cài)")
    g3 = QGridLayout(grp_entry)
    g3.setSpacing(8)

    g3.addWidget(QLabel("Loại"), 0, 0)
    cmb_entry_type = QComboBox()
    cmb_entry_type.addItems(["bash", "python", "binary", "(không có)"])
    g3.addWidget(cmb_entry_type, 0, 1)

    g3.addWidget(QLabel("File entry"), 1, 0)
    le_entry = QLineEdit("main.sh")
    fields["entry"] = le_entry
    g3.addWidget(le_entry, 1, 1)

    t1.addWidget(grp_entry)
    t1.addStretch()
    tabs.addTab(tab_info, "📝  Thông tin")

    # ── Tab 2: Files ──────────────────────────────────────────────
    tab_files = QWidget()
    t2 = QVBoxLayout(tab_files)
    t2.setSpacing(8)

    install_rules = []  # list of dicts

    lbl_rules = QLabel("Danh sách file cài vào hệ thống:")
    lbl_rules.setStyleSheet("color: #8b949e;")
    t2.addWidget(lbl_rules)

    list_rules = QListWidget()
    t2.addWidget(list_rules, 1)

    # Add rule row
    add_row = QHBoxLayout()
    le_src = QLineEdit(); le_src.setPlaceholderText("files/myapp.py  (trong zip)")
    le_dst = QLineEdit(); le_dst.setPlaceholderText("{desktop}/myapp.py")
    chk_exe = QCheckBox("executable")
    btn_add_rule = QPushButton("+ Thêm"); btn_add_rule.setObjectName("btnAdd")
    add_row.addWidget(QLabel("Src:")); add_row.addWidget(le_src, 2)
    add_row.addWidget(QLabel("Dest:")); add_row.addWidget(le_dst, 2)
    add_row.addWidget(chk_exe)
    add_row.addWidget(btn_add_rule)
    t2.addLayout(add_row)

    def add_rule():
        src = le_src.text().strip()
        dst = le_dst.text().strip()
        if not src or not dst:
            return
        rule = {"src": src, "dest": dst, "executable": chk_exe.isChecked()}
        install_rules.append(rule)
        exe_tag = " [exe]" if rule["executable"] else ""
        list_rules.addItem(f"{src}  →  {dst}{exe_tag}")
        le_src.clear(); le_dst.clear(); chk_exe.setChecked(False)

    def remove_rule():
        row = list_rules.currentRow()
        if row >= 0:
            list_rules.takeItem(row)
            install_rules.pop(row)

    btn_add_rule.clicked.connect(add_rule)

    btn_rm = QPushButton("✕ Xóa dòng được chọn")
    btn_rm.clicked.connect(remove_rule)
    t2.addWidget(btn_rm)

    # Hint
    hint = QLabel(
        "Path variables: {desktop} {documents} {pictures} {downloads} "
        "{music} {videos} {home} {tmp} {C} {D} {E} {apps} {bin}"
    )
    hint.setStyleSheet("color: #484f58; font-size: 11px;")
    hint.setWordWrap(True)
    t2.addWidget(hint)
    tabs.addTab(tab_files, "📂  Files")

    # ── Tab 3: Source & Build ─────────────────────────────────────
    tab_build = QWidget()
    t3 = QVBoxLayout(tab_build)
    t3.setSpacing(10)

    grp_src = QGroupBox("Thư mục nguồn")
    g_src = QHBoxLayout(grp_src)
    le_src_dir = QLineEdit(); le_src_dir.setPlaceholderText("Chọn thư mục chứa file của bạn...")
    btn_browse  = QPushButton("📁 Chọn")
    g_src.addWidget(le_src_dir); g_src.addWidget(btn_browse)
    t3.addWidget(grp_src)

    grp_out = QGroupBox("Output")
    g_out = QHBoxLayout(grp_out)
    le_out = QLineEdit(); le_out.setPlaceholderText("myapp.mxl")
    btn_out = QPushButton("📁 Lưu thành")
    g_out.addWidget(le_out); g_out.addWidget(btn_out)
    t3.addWidget(grp_out)

    log_build = QTextEdit()
    log_build.setReadOnly(True)
    log_build.setPlaceholderText("Log build sẽ hiện ở đây...")
    t3.addWidget(log_build, 1)
    tabs.addTab(tab_build, "🔨  Build")

    def browse_src():
        d = QFileDialog.getExistingDirectory(win, "Chọn thư mục nguồn")
        if d: le_src_dir.setText(d)

    def browse_out():
        f, _ = QFileDialog.getSaveFileName(win, "Lưu file .mxl", "", "MXL Package (*.mxl)")
        if f: le_out.setText(f)

    btn_browse.clicked.connect(browse_src)
    btn_out.clicked.connect(browse_out)

    # ── Build button ──────────────────────────────────────────────
    btn_build = QPushButton("🚀  BUILD .MXL")
    btn_build.setObjectName("btnBuild")

    def do_build():
        src_dir = le_src_dir.text().strip()
        out     = le_out.text().strip() or fields["name"].text().strip().lower().replace(" ","_") + ".mxl"

        if not src_dir or not os.path.isdir(src_dir):
            QMessageBox.warning(win, "Lỗi", "Chọn thư mục nguồn hợp lệ!")
            return

        # Build manifest
        entry_type_val = cmb_entry_type.currentText()
        manifest = {
            "name":         fields["name"].text().strip()    or "My App",
            "version":      fields["version"].text().strip() or "1.0",
            "author":       fields["author"].text().strip()  or "Unknown",
            "description":  fields["desc"].text().strip(),
            "ui":           cmb_ui.currentText(),
            "theme":        cmb_theme.currentText(),
            "window_title": le_title.text().strip(),
            "window_size":  [sb_w.value(), sb_h.value()],
            "entry_type":   entry_type_val if entry_type_val != "(không có)" else None,
            "entry":        fields["entry"].text().strip() if entry_type_val != "(không có)" else None,
            "install_rules": install_rules,
        }

        # Ghi manifest vào src_dir
        mpath = os.path.join(src_dir, "manifest.json")
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        log_build.clear()
        log_build.append(f"[*] Build bắt đầu...\n    Src: {src_dir}\n    Out: {out}\n")

        try:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(src_dir):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for fname in files:
                        fp = os.path.join(root, fname)
                        arc = os.path.relpath(fp, src_dir)
                        zf.write(fp, arc)
                        log_build.append(f"  + {arc}")

            size = os.path.getsize(out)
            log_build.append(f"\n✅ Thành công!\n   File: {out}\n   Size: {size/1024:.1f} KB")
            tabs.setCurrentIndex(2)
        except Exception as e:
            log_build.append(f"\n❌ Lỗi: {e}")

    btn_build.clicked.connect(do_build)
    main_layout.addWidget(btn_build)

    win.show()
    sys.exit(app.exec())


# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MXL Builder")
    parser.add_argument("--gui",    action="store_true", help="Mở giao diện đồ họa")
    parser.add_argument("--init",   metavar="DIR",       help="Tạo manifest.json mẫu trong thư mục")
    parser.add_argument("--build",  metavar="DIR",       help="Build .mxl từ thư mục")
    parser.add_argument("--output", metavar="FILE",      help="Tên file output .mxl")
    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        build_gui()
    elif args.init:
        os.makedirs(args.init, exist_ok=True)
        mpath = os.path.join(args.init, "manifest.json")
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(MANIFEST_TEMPLATE, f, ensure_ascii=False, indent=2)
        # Tạo file mẫu
        with open(os.path.join(args.init, "main.sh"), "w") as f:
            f.write("#!/bin/bash\necho 'Hello from MXL!'\n")
        os.makedirs(os.path.join(args.init, "files"), exist_ok=True)
        print(f"✓ Khởi tạo project tại: {args.init}")
        print(f"  Sửa manifest.json → chạy: mxl-builder --build {args.init}")
    elif args.build:
        build_terminal(args.output or "", args.build)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
