#!/usr/bin/env python3
"""Settings – MixtralOS (full Control Panel, Windows-style)"""
import json, os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QComboBox, QFrame,
    QScrollArea, QSizePolicy, QStackedWidget, QMessageBox,
    QSlider, QCheckBox, QSpinBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

CFG = os.path.expanduser("~/.config/mixtralr/config.json")

try:
    from desktop import DEFAULT_WALLPAPER, THEMES
except ImportError:
    DEFAULT_WALLPAPER = ""
    THEMES = {}

CATEGORIES = [
    ("🎨", "Appearance",    "Theme, wallpaper, colors"),
    ("🖥", "Display",       "Resolution, font size"),
    ("🔊", "Sound",         "Volume, devices"),
    ("🌐", "Network",       "Wi-Fi, Ethernet, VPN"),
    ("👤", "Accounts",      "User profile, password"),
    ("⏰", "Time & Date",   "Clock, timezone, format"),
    ("🔒", "Privacy",       "Screen lock, password"),
    ("♿", "Accessibility",  "Display, interaction"),
    ("🔄", "Updates",       "System updates"),
    ("ℹ",  "About",         "System info, version"),
]


def _load_cfg():
    try:
        with open(CFG) as f: return json.load(f)
    except Exception: return {}

def _save_cfg(data):
    try:
        d = _load_cfg()
        d.update(data)
        os.makedirs(os.path.dirname(CFG), exist_ok=True)
        with open(CFG,"w") as f: json.dump(d,f,indent=2)
    except Exception: pass


# ── Category card ─────────────────────────────────────────────────
class CategoryCard(QWidget):
    def __init__(self, icon, title, desc, on_click):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(192, 96)
        self._clicked = on_click
        self.setObjectName("CatCard")
        self._hovered = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        row = QHBoxLayout()
        ico = QLabel(icon); ico.setFont(QFont("Segoe UI Emoji", 24))
        ico.setFixedWidth(36); ico.setStyleSheet("background:transparent;border:none;")
        tlbl = QLabel(title)
        tlbl.setFont(QFont("DejaVu Sans", 11, QFont.Weight.Bold))
        tlbl.setStyleSheet("background:transparent;border:none;")
        row.addWidget(ico); row.addWidget(tlbl); row.addStretch()

        dlbl = QLabel(desc)
        dlbl.setFont(QFont("DejaVu Sans", 9))
        dlbl.setObjectName("CatDesc")
        dlbl.setWordWrap(True)
        dlbl.setStyleSheet("color:#8b949e;background:transparent;border:none;")

        lay.addLayout(row); lay.addWidget(dlbl)
        self._apply_style(False)

    def _apply_style(self, hovered):
        if hovered:
            self.setStyleSheet(
                "QWidget#CatCard{background:#21262d;border:1px solid #58a6ff;border-radius:10px;}")
        else:
            self.setStyleSheet(
                "QWidget#CatCard{background:#161b22;border:1px solid #30363d;border-radius:10px;}")

    def enterEvent(self,e): self._apply_style(True)
    def leaveEvent(self,e): self._apply_style(False)
    def mousePressEvent(self,e): self._clicked()


# ── Wallpaper preview ─────────────────────────────────────────────
class WallpaperPreview(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(192, 108)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "border:1px solid #30363d;border-radius:8px;background:#0d1117;")
        self.setText("(no image)")

    def load(self, path):
        resolved = path if (path and os.path.isfile(path)) else DEFAULT_WALLPAPER
        if resolved and os.path.isfile(resolved):
            pix = QPixmap(resolved)
            if not pix.isNull():
                self.setPixmap(pix.scaled(self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation))
                self.setText(""); return
        self.setPixmap(QPixmap()); self.setText("(no image)")


# ── Appearance page ───────────────────────────────────────────────
class AppearancePage(QWidget):
    def __init__(self, desktop, go_back):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(14)

        # Back + title
        hdr = QHBoxLayout()
        back = QPushButton("← Back"); back.setFixedSize(80,30); back.clicked.connect(go_back)
        title = QLabel("🎨  Appearance")
        title.setFont(QFont("DejaVu Sans",16,QFont.Weight.Bold))
        hdr.addWidget(back); hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;}
            QTabBar::tab{background:#161b22;color:#8b949e;padding:8px 20px;
                border:1px solid #30363d;border-bottom:none;border-radius:4px 4px 0 0;}
            QTabBar::tab:selected{background:#21262d;color:#58a6ff;}
        """)
        lay.addWidget(tabs, stretch=1)

        # ── Theme tab ─────────────────────────────────────────────
        theme_tab = QWidget()
        tt_lay = QVBoxLayout(theme_tab)
        tt_lay.setContentsMargins(16,16,16,16); tt_lay.setSpacing(12)
        tt_lay.addWidget(self._sec("Theme"))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()) or ["neon-dark","cyber-green","midnight-purple","ocean-blue","sunset-dark"])
        self.theme_combo.setFixedHeight(36)
        self.theme_combo.currentTextChanged.connect(
            lambda t: desktop.apply_theme(t) if desktop else None)
        tt_lay.addWidget(self.theme_combo)

        # Preview colors
        self._color_row = QHBoxLayout()
        self._color_lbls = {}
        for key, label in [("bg","BG"),("surface","Surface"),("accent","Accent"),("text","Text")]:
            col_w = QWidget(); col_w.setFixedSize(60,40)
            col_w.setObjectName(f"color_{key}")
            col_lay = QVBoxLayout(col_w); col_lay.setContentsMargins(0,0,0,0)
            lbl = QLabel(label); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("DejaVu Sans",8))
            col_lay.addWidget(lbl)
            self._color_row.addWidget(col_w)
            self._color_lbls[key] = col_w
        self._color_row.addStretch()
        tt_lay.addLayout(self._color_row)
        self.theme_combo.currentTextChanged.connect(self._update_colors)

        tt_lay.addWidget(self._sec("Font"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["DejaVu Sans","Ubuntu","Noto Sans","Liberation Sans","Monospace"])
        self.font_combo.setFixedHeight(34)
        tt_lay.addStretch()
        tabs.addTab(theme_tab, "🎨 Theme")

        # ── Wallpaper tab ─────────────────────────────────────────
        wall_tab = QWidget()
        wt_lay = QVBoxLayout(wall_tab)
        wt_lay.setContentsMargins(16,16,16,16); wt_lay.setSpacing(10)

        # Preview + status row
        prev_row = QHBoxLayout()
        self._preview = WallpaperPreview()
        prev_col = QVBoxLayout()
        prev_col.addWidget(self._preview)

        self._status_lbl = QLabel("🏠 Using default")
        self._status_lbl.setFont(QFont("DejaVu Sans",9))
        self._status_lbl.setStyleSheet("color:#58a6ff;")
        prev_col.addWidget(self._status_lbl)
        prev_row.addLayout(prev_col)
        prev_row.addStretch()
        wt_lay.addLayout(prev_row)

        # Input row
        input_row = QHBoxLayout()
        self.wall_edit = QLineEdit()
        self.wall_edit.setPlaceholderText("Leave empty for default wallpaper...")
        self.wall_edit.setFixedHeight(34)
        self.wall_edit.textChanged.connect(self._on_wall_changed)
        browse_btn = QPushButton("📂 Browse"); browse_btn.setFixedSize(100,34)
        browse_btn.clicked.connect(self._browse)
        reset_btn  = QPushButton("↩ Default"); reset_btn.setFixedSize(100,34)
        reset_btn.clicked.connect(lambda: self.wall_edit.setText(""))
        input_row.addWidget(self.wall_edit)
        input_row.addWidget(browse_btn)
        input_row.addWidget(reset_btn)
        wt_lay.addLayout(input_row)

        note = QLabel("💡 Default wallpaper (mixtralr-ui-d.png) is protected and cannot be deleted.")
        note.setFont(QFont("DejaVu Sans",9))
        note.setStyleSheet("color:#8b949e;")
        note.setWordWrap(True)
        wt_lay.addWidget(note)
        wt_lay.addStretch()
        tabs.addTab(wall_tab, "🖼 Wallpaper")

        # ── Save button ───────────────────────────────────────────
        save_btn = QPushButton("✅  Save & Apply")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(lambda: self._save(desktop))
        save_btn.setStyleSheet(
            "QPushButton{background:#1a4a9f;color:#fff;border:none;border-radius:8px;font-weight:bold;}"
            "QPushButton:hover{background:#2060cf;}"
        )
        lay.addWidget(save_btn)
        self._desktop = desktop
        self._load()
        self._update_colors(self.theme_combo.currentText())

    def _sec(self, txt):
        l = QLabel(txt); l.setFont(QFont("DejaVu Sans",11,QFont.Weight.Bold))
        return l

    def _update_colors(self, theme_name):
        if not THEMES: return
        t = THEMES.get(theme_name, {})
        for key, w in self._color_lbls.items():
            c = t.get(key, "#333")
            w.setStyleSheet(f"background:{c}; border-radius:6px;")

    def _on_wall_changed(self, text):
        self._preview.load(text)
        if not text.strip():
            self._status_lbl.setText("🏠 Using default wallpaper")
        elif os.path.isfile(text):
            self._status_lbl.setText("✅ Custom wallpaper OK")
        else:
            self._status_lbl.setText("⚠️  File not found")

    def _load(self):
        d = _load_cfg()
        idx = self.theme_combo.findText(d.get("theme","neon-dark"))
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)
        wall = d.get("wallpaper","")
        if wall and DEFAULT_WALLPAPER and os.path.normpath(wall)==os.path.normpath(DEFAULT_WALLPAPER):
            wall = ""
        self.wall_edit.setText(wall)
        fi = self.font_combo.findText(d.get("font","DejaVu Sans"))
        if fi >= 0: self.font_combo.setCurrentIndex(fi)
        self._on_wall_changed(self.wall_edit.text())

    def _browse(self):
        start = os.path.dirname(self.wall_edit.text()) if self.wall_edit.text() else os.path.expanduser("~")
        f, _ = QFileDialog.getOpenFileName(self,"Choose Wallpaper",start,
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if f:
            if DEFAULT_WALLPAPER and os.path.normpath(f)==os.path.normpath(DEFAULT_WALLPAPER):
                self.wall_edit.setText("")
            else:
                self.wall_edit.setText(f)

    def _save(self, desktop):
        raw = self.wall_edit.text().strip()
        if raw and DEFAULT_WALLPAPER and os.path.normpath(raw)==os.path.normpath(DEFAULT_WALLPAPER):
            raw = ""
        if raw and not os.path.isfile(raw):
            r = QMessageBox.question(self,"File Not Found",
                f"File does not exist:\n{raw}\nUse default wallpaper instead?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            if r==QMessageBox.StandardButton.No: return
            raw = ""
        data = {"theme": self.theme_combo.currentText(),
                "wallpaper": raw,
                "font": self.font_combo.currentText()}
        if desktop:
            desktop.save_config(data)
            desktop.notify("✅ Settings","Appearance saved.")
        else:
            _save_cfg(data)


# ── Sound page ────────────────────────────────────────────────────
class SoundPage(QWidget):
    def __init__(self, go_back):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28,20,28,20); lay.setSpacing(14)
        hdr = QHBoxLayout()
        back = QPushButton("← Back"); back.setFixedSize(80,30); back.clicked.connect(go_back)
        title = QLabel("🔊  Sound")
        title.setFont(QFont("DejaVu Sans",16,QFont.Weight.Bold))
        hdr.addWidget(back); hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        lay.addWidget(QLabel("Master Volume").setFont(QFont("DejaVu Sans",11,QFont.Weight.Bold)) or QLabel("Master Volume"))
        vol_row = QHBoxLayout()
        self._vol_lbl = QLabel("🔊"); self._vol_lbl.setFont(QFont("Segoe UI Emoji",18))
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0,100)
        self._vol_slider.setValue(_load_cfg().get("volume",75))
        self._vol_slider.setFixedHeight(20)
        self._vol_pct = QLabel(f"{self._vol_slider.value()}%")
        self._vol_slider.valueChanged.connect(lambda v: (
            self._vol_pct.setText(f"{v}%"),
            self._vol_lbl.setText("🔇" if v==0 else "🔉" if v<40 else "🔊"),
            _save_cfg({"volume": v})
        ))
        vol_row.addWidget(self._vol_lbl)
        vol_row.addWidget(self._vol_slider, stretch=1)
        vol_row.addWidget(self._vol_pct)
        lay.addLayout(vol_row)
        lay.addStretch()


# ── Privacy / Lock page ───────────────────────────────────────────
class PrivacyPage(QWidget):
    def __init__(self, desktop, go_back):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28,20,28,20); lay.setSpacing(14)
        hdr = QHBoxLayout()
        back = QPushButton("← Back"); back.setFixedSize(80,30); back.clicked.connect(go_back)
        title = QLabel("🔒  Privacy & Security")
        title.setFont(QFont("DejaVu Sans",16,QFont.Weight.Bold))
        hdr.addWidget(back); hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        sec = QLabel("Screen Lock Password")
        sec.setFont(QFont("DejaVu Sans",12,QFont.Weight.Bold)); lay.addWidget(sec)

        note = QLabel("Leave blank = no password (any Enter unlocks).")
        note.setStyleSheet("color:#8b949e;"); lay.addWidget(note)

        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("New lock password (leave blank to disable)...")
        self._pw.setFixedHeight(36)
        lay.addWidget(self._pw)

        self._pw2 = QLineEdit()
        self._pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw2.setPlaceholderText("Confirm password...")
        self._pw2.setFixedHeight(36)
        lay.addWidget(self._pw2)

        save_btn = QPushButton("🔒  Save Password")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(
            "background:#1a4a9f;color:#fff;border:none;border-radius:8px;font-weight:bold;"
        )
        save_btn.clicked.connect(lambda: self._save_pw(desktop))
        lay.addWidget(save_btn)

        lock_now = QPushButton("🔒  Lock Screen Now")
        lock_now.setFixedHeight(38)
        lock_now.clicked.connect(lambda: desktop._lock_screen() if desktop else None)
        lay.addWidget(lock_now)
        lay.addStretch()

    def _save_pw(self, desktop):
        p1 = self._pw.text()
        p2 = self._pw2.text()
        if p1 != p2:
            QMessageBox.warning(self,"Mismatch","Passwords do not match!"); return
        _save_cfg({"lock_password": p1})
        if desktop: desktop.notify("✅ Password","Lock password saved.")
        self._pw.clear(); self._pw2.clear()


# ── About page ────────────────────────────────────────────────────
class AboutPage(QWidget):
    def __init__(self, go_back):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28,20,28,20); lay.setSpacing(14)
        hdr = QHBoxLayout()
        back = QPushButton("← Back"); back.setFixedSize(80,30); back.clicked.connect(go_back)
        title = QLabel("ℹ  About Mixtralr OS")
        title.setFont(QFont("DejaVu Sans",16,QFont.Weight.Bold))
        hdr.addWidget(back); hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Logo
        logo = QLabel("⚡"); logo.setFont(QFont("Segoe UI Emoji",56))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)

        info = [
            ("OS Name",     "Mixtralr OS"),
            ("Version",     "2.0.0  (MixtralOS Enhanced)"),
            ("Desktop",     "Mixtralr Shell (PyQt6)"),
            ("Kernel",      "Linux"),
            ("Architecture","x86_64"),
            ("Python",      __import__("sys").version.split()[0]),
            ("Qt",          __import__("PyQt6.QtCore",fromlist=["QT_VERSION_STR"]).QT_VERSION_STR),
        ]
        for k, v in info:
            row = QHBoxLayout()
            kl = QLabel(k); kl.setFont(QFont("DejaVu Sans",11,QFont.Weight.Bold))
            kl.setFixedWidth(130)
            vl = QLabel(v); vl.setFont(QFont("DejaVu Sans",11))
            vl.setStyleSheet("color:#58a6ff;")
            row.addWidget(kl); row.addWidget(vl); row.addStretch()
            lay.addLayout(row)
        lay.addStretch()


# ── Main Settings window ──────────────────────────────────────────
class MixtralrSettings(QWidget):
    def __init__(self, desktop=None):
        super().__init__()
        self.desktop = desktop
        self.setWindowTitle("⚙  Settings")
        self.setMinimumSize(760, 540)

        main = QVBoxLayout(self)
        main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # Header
        header = QWidget(); header.setFixedHeight(56)
        header.setStyleSheet("background:#161b22; border-bottom:1px solid #30363d;")
        hl = QHBoxLayout(header); hl.setContentsMargins(20,8,20,8)
        title_lbl = QLabel("⚙  Settings")
        title_lbl.setFont(QFont("DejaVu Sans",14,QFont.Weight.Bold))
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Find a setting")
        self.search.setFixedSize(240,32)
        self.search.textChanged.connect(self._filter)
        hl.addWidget(title_lbl); hl.addStretch(); hl.addWidget(self.search)
        main.addWidget(header)

        self.stack = QStackedWidget()
        main.addWidget(self.stack)

        # ── Home scroll ───────────────────────────────────────────
        home_scroll = QScrollArea(); home_scroll.setWidgetResizable(True)
        home_scroll.setFrameShape(QFrame.Shape.NoFrame)
        home_scroll.setStyleSheet("background:transparent;")
        home_widget = QWidget(); home_widget.setStyleSheet("background:transparent;")
        home_scroll.setWidget(home_widget)
        self.grid = QGridLayout(home_widget)
        self.grid.setContentsMargins(24,24,24,24); self.grid.setSpacing(12)
        self._cards = []
        self.stack.addWidget(home_scroll)  # index 0

        # ── Detail pages ──────────────────────────────────────────
        self._appear_page  = AppearancePage(desktop, self._home)
        self._sound_page   = SoundPage(self._home)
        self._privacy_page = PrivacyPage(desktop, self._home)
        self._about_page   = AboutPage(self._home)

        self.stack.addWidget(self._appear_page)   # 1
        self.stack.addWidget(self._sound_page)    # 2
        self.stack.addWidget(self._privacy_page)  # 3
        self.stack.addWidget(self._about_page)    # 4

        # Placeholder pages for other categories
        for _ in range(len(CATEGORIES) - 4):
            self.stack.addWidget(self._placeholder())

        self._build_grid(CATEGORIES)

    def _placeholder(self):
        w = QWidget(); l = QVBoxLayout(w)
        back = QPushButton("← Back"); back.setFixedSize(80,30)
        back.clicked.connect(self._home)
        lbl = QLabel("🚧  Coming Soon")
        lbl.setFont(QFont("DejaVu Sans",16))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(back); l.addStretch(); l.addWidget(lbl); l.addStretch()
        return w

    def _build_grid(self, cats):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()
        page_map = {
            "Appearance": 1, "Sound": 2, "Privacy": 3, "About": 4,
        }
        placeholder_idx = 5
        for idx, (icon, title, desc) in enumerate(cats):
            if title in page_map:
                pg = page_map[title]
            else:
                pg = placeholder_idx
                placeholder_idx += 1
            card = CategoryCard(icon, title, desc,
                                lambda p=pg: self.stack.setCurrentIndex(p))
            self._cards.append(card)
            self.grid.addWidget(card, idx // 3, idx % 3)

    def _home(self):
        self.stack.setCurrentIndex(0)

    def _filter(self, text):
        if not text:
            self._build_grid(CATEGORIES); return
        t = text.lower()
        self._build_grid([c for c in CATEGORIES
                          if t in c[1].lower() or t in c[2].lower()])
