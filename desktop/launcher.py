#!/usr/bin/env python3
"""
Launcher – MixtralOS (Windows Start Menu style)
- Search bar
- App grid với categories
- Recent files
- User info + power menu
"""
import os, json, subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QLineEdit, QScrollArea, QGridLayout,
    QSizePolicy, QStackedWidget
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient

CONFIG_PATH = os.path.expanduser("~/.config/mixtralr/config.json")

# ── App registry ─────────────────────────────────────────────────
ALL_APPS = [
    # (emoji, name, desc, module, classname, category)
    ("🖥",  "Terminal",     "Run shell commands",      "terminal",    "MixtralrTerminal",    "System"),
    ("📁",  "Explorer",     "Browse your files",       "explorer",    "MixtralrExplorer",    "System"),
    ("🌐",  "Browser",      "Surf the internet",       "browser",     "MixtralrBrowser",     "Internet"),
    ("📝",  "Text Editor",  "Edit text and code",      "texteditor",  "MixtralrTextEditor",  "Productivity"),
    ("🧮",  "Calculator",   "Math & calculations",     "calculator",  "MixtralrCalculator",  "Utilities"),
    ("🖼",  "Image Viewer", "View & browse images",    "imageviewer", "MixtralrImageViewer", "Media"),
    ("📊",  "Task Manager", "Monitor processes & CPU", "taskmanager", "MixtralrTaskManager", "System"),
    ("⚙",  "Settings",     "Configure the desktop",   "settings",    "MixtralrSettings",    "System"),
]

CATEGORIES = ["All", "System", "Productivity", "Utilities", "Internet", "Media"]


def _load_recent():
    try:
        with open(CONFIG_PATH) as f:
            d = json.load(f)
        return d.get("recent_apps", [])
    except Exception:
        return []


def _save_recent(name):
    try:
        d = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                d = json.load(f)
        recent = d.get("recent_apps", [])
        if name in recent:
            recent.remove(name)
        recent.insert(0, name)
        d["recent_apps"] = recent[:8]
        with open(CONFIG_PATH, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


# ── App tile button ───────────────────────────────────────────────
class AppTile(QWidget):
    def __init__(self, emoji, name, desc, on_click):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clicked = on_click
        self.setFixedSize(130, 80)
        self._hovered = False
        self.setObjectName("AppTile")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ico = QLabel(emoji)
        ico.setFont(QFont("Segoe UI Emoji", 26))
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setStyleSheet("background:transparent; border:none;")

        nm = QLabel(name)
        nm.setFont(QFont("DejaVu Sans", 9, QFont.Weight.Bold))
        nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nm.setStyleSheet("background:transparent; border:none; color:#e6edf3;")
        nm.setWordWrap(True)

        lay.addWidget(ico)
        lay.addWidget(nm)
        self._apply_style(False)

    def _apply_style(self, hovered):
        if hovered:
            self.setStyleSheet(
                "QWidget#AppTile{background:#21262d; border:1px solid #58a6ff;"
                "border-radius:10px;}"
            )
        else:
            self.setStyleSheet(
                "QWidget#AppTile{background:#161b22; border:1px solid #30363d;"
                "border-radius:10px;}"
            )

    def enterEvent(self, e):
        self._apply_style(True)

    def leaveEvent(self, e):
        self._apply_style(False)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._clicked()


# ── Compact list row (search results) ────────────────────────────
class AppRow(QPushButton):
    def __init__(self, emoji, name, desc, on_click):
        super().__init__()
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(on_click)
        self.setStyleSheet("""
            QPushButton{background:transparent; border:none; border-radius:6px;
                text-align:left; padding:0 8px;}
            QPushButton:hover{background:#21262d;}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(10)

        ico = QLabel(emoji); ico.setFont(QFont("Segoe UI Emoji", 18))
        ico.setFixedWidth(28); ico.setStyleSheet("background:transparent;")
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info = QVBoxLayout(); info.setSpacing(1)
        nm = QLabel(name); nm.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
        nm.setStyleSheet("color:#e6edf3; background:transparent;")
        ds = QLabel(desc); ds.setFont(QFont("DejaVu Sans", 8))
        ds.setStyleSheet("color:#8b949e; background:transparent;")
        info.addWidget(nm); info.addWidget(ds)

        lay.addWidget(ico)
        lay.addLayout(info)
        lay.addStretch()


# ── Main launcher window ──────────────────────────────────────────
class Launcher(QWidget):
    def __init__(self, desktop):
        super().__init__(desktop)
        self.desktop = desktop
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(560, 580)
        self._visible = False

        # Outer layout: just holds the card
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Card
        self._card = QWidget()
        self._card.setObjectName("LauncherCard")
        self._card.setStyleSheet("""
            QWidget#LauncherCard{
                background: rgba(13,17,23,0.97);
                border: 1px solid #30363d;
                border-radius: 14px;
            }
        """)
        outer.addWidget(self._card)

        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        # ── Top: user info ────────────────────────────────────────
        top_row = QHBoxLayout()
        try:
            with open(CONFIG_PATH) as f:
                username = json.load(f).get("username", os.getenv("USER", "User"))
        except Exception:
            username = os.getenv("USER", "User")

        ava = QLabel("👤"); ava.setFont(QFont("Segoe UI Emoji", 22))
        ava.setStyleSheet("background:transparent;")
        user_lbl = QLabel(username)
        user_lbl.setFont(QFont("DejaVu Sans", 13, QFont.Weight.Bold))
        user_lbl.setStyleSheet("color:#e6edf3; background:transparent;")

        top_row.addWidget(ava)
        top_row.addWidget(user_lbl)
        top_row.addStretch()
        card_lay.addLayout(top_row)

        # ── Search ────────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search apps...")
        self._search.setFixedHeight(38)
        self._search.setStyleSheet("""
            QLineEdit{background:#21262d; border:1px solid #30363d; border-radius:8px;
                padding:4px 12px; color:#e6edf3; font-size:12px;}
            QLineEdit:focus{border-color:#58a6ff;}
        """)
        self._search.textChanged.connect(self._on_search)
        card_lay.addWidget(self._search)

        # ── Stacked: grid view vs search results ──────────────────
        self._stack = QStackedWidget()
        card_lay.addWidget(self._stack, stretch=1)

        # Page 0: Category + app grid
        grid_page = QWidget()
        grid_page.setStyleSheet("background:transparent;")
        gp_lay = QVBoxLayout(grid_page)
        gp_lay.setContentsMargins(0, 0, 0, 0)
        gp_lay.setSpacing(8)

        # Category tabs
        cat_row = QHBoxLayout()
        cat_row.setSpacing(4)
        self._cat_btns = []
        for cat in CATEGORIES:
            b = QPushButton(cat)
            b.setFixedHeight(26)
            b.setCheckable(True)
            b.setFont(QFont("DejaVu Sans", 9))
            b.setStyleSheet("""
                QPushButton{background:#21262d;color:#8b949e;border:1px solid #30363d;
                    border-radius:5px;padding:2px 10px;}
                QPushButton:checked{background:#58a6ff;color:#0d1117;border-color:#58a6ff;}
                QPushButton:hover{color:#e6edf3;border-color:#58a6ff;}
            """)
            b.clicked.connect(lambda _, c=cat: self._filter_category(c))
            cat_row.addWidget(b)
            self._cat_btns.append((cat, b))
        cat_row.addStretch()
        gp_lay.addLayout(cat_row)
        self._cat_btns[0][1].setChecked(True)

        # App grid scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:transparent;")
        self._grid_lay = QGridLayout(self._grid_widget)
        self._grid_lay.setSpacing(8)
        self._grid_lay.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._grid_widget)
        gp_lay.addWidget(scroll, stretch=1)

        # Recent apps label
        sep_r = QFrame(); sep_r.setFrameShape(QFrame.Shape.HLine)
        sep_r.setStyleSheet("background:#30363d;")
        gp_lay.addWidget(sep_r)

        recent_hdr = QLabel("🕐  Recent")
        recent_hdr.setFont(QFont("DejaVu Sans", 9))
        recent_hdr.setStyleSheet("color:#8b949e; background:transparent;")
        gp_lay.addWidget(recent_hdr)

        self._recent_row = QHBoxLayout()
        self._recent_row.setSpacing(6)
        gp_lay.addLayout(self._recent_row)

        self._stack.addWidget(grid_page)

        # Page 1: Search results
        search_page = QWidget()
        search_page.setStyleSheet("background:transparent;")
        sp_lay = QVBoxLayout(search_page)
        sp_lay.setContentsMargins(0, 0, 0, 0)
        sp_lay.setSpacing(4)
        self._search_results = QWidget()
        self._search_results.setStyleSheet("background:transparent;")
        self._sr_lay = QVBoxLayout(self._search_results)
        self._sr_lay.setContentsMargins(0, 0, 0, 0)
        self._sr_lay.setSpacing(2)
        sp_scroll = QScrollArea()
        sp_scroll.setWidgetResizable(True)
        sp_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sp_scroll.setStyleSheet("background:transparent;")
        sp_scroll.setWidget(self._search_results)
        sp_lay.addWidget(sp_scroll)
        self._stack.addWidget(search_page)

        # ── Bottom: power row ─────────────────────────────────────
        sep_bot = QFrame(); sep_bot.setFrameShape(QFrame.Shape.HLine)
        sep_bot.setStyleSheet("background:#30363d;")
        card_lay.addWidget(sep_bot)

        power_row = QHBoxLayout()
        power_row.setSpacing(6)

        def pwr(icon, label, slot):
            b = QPushButton(f"{icon}  {label}")
            b.setFixedHeight(32)
            b.setFont(QFont("DejaVu Sans", 9))
            b.clicked.connect(slot)
            b.setStyleSheet("""
                QPushButton{background:#21262d;color:#e6edf3;border:1px solid #30363d;
                    border-radius:6px;padding:4px 12px;}
                QPushButton:hover{border-color:#f85149;color:#f85149;}
            """)
            return b

        power_row.addStretch()
        power_row.addWidget(pwr("🔒", "Lock",     self._lock))
        power_row.addWidget(pwr("🔄", "Restart",  self._restart))
        power_row.addWidget(pwr("⏻",  "Shutdown", self._shutdown))
        card_lay.addLayout(power_row)

        # Build initial grid
        self._build_grid(ALL_APPS)
        self._refresh_recent()

    # ── Grid builder ─────────────────────────────────────────────
    def _build_grid(self, apps):
        while self._grid_lay.count():
            item = self._grid_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        cols = 4
        for idx, app in enumerate(apps):
            emoji, name, desc, mod, cls_name, cat = app
            tile = AppTile(emoji, name, desc,
                           lambda m=mod, c=cls_name, n=name: self._launch(m, c, n))
            self._grid_lay.addWidget(tile, idx // cols, idx % cols)

        # Fill remaining cells
        remainder = len(apps) % cols
        if remainder:
            for i in range(cols - remainder):
                ph = QWidget(); ph.setFixedSize(130, 80)
                ph.setStyleSheet("background:transparent;")
                self._grid_lay.addWidget(ph,
                    len(apps) // cols, remainder + i)

    def _filter_category(self, cat):
        for c, b in self._cat_btns:
            b.setChecked(c == cat)
        if cat == "All":
            self._build_grid(ALL_APPS)
        else:
            self._build_grid([a for a in ALL_APPS if a[5] == cat])

    def _refresh_recent(self):
        while self._recent_row.count():
            item = self._recent_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        recent = _load_recent()
        shown = 0
        for name in recent[:5]:
            for app in ALL_APPS:
                if app[1] == name:
                    emoji, nm, desc, mod, cls_name, _ = app
                    btn = QPushButton(f"{emoji} {nm}")
                    btn.setFixedHeight(28)
                    btn.setFont(QFont("DejaVu Sans", 9))
                    btn.clicked.connect(
                        lambda m=mod, c=cls_name, n=nm: self._launch(m, c, n))
                    btn.setStyleSheet("""
                        QPushButton{background:#21262d;color:#e6edf3;border:1px solid #30363d;
                            border-radius:5px;padding:2px 8px;}
                        QPushButton:hover{border-color:#58a6ff;color:#58a6ff;}
                    """)
                    self._recent_row.addWidget(btn)
                    shown += 1
                    break
        self._recent_row.addStretch()

    # ── Search ────────────────────────────────────────────────────
    def _on_search(self, text):
        if not text.strip():
            self._stack.setCurrentIndex(0)
            return
        self._stack.setCurrentIndex(1)
        # Clear old results
        while self._sr_lay.count():
            item = self._sr_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        t = text.lower()
        results = [a for a in ALL_APPS
                   if t in a[1].lower() or t in a[2].lower() or t in a[5].lower()]
        if not results:
            lbl = QLabel("No results found")
            lbl.setStyleSheet("color:#8b949e; padding:20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._sr_lay.addWidget(lbl)
        else:
            for emoji, name, desc, mod, cls_name, cat in results:
                row = AppRow(emoji, name, desc,
                             lambda m=mod, c=cls_name, n=name: self._launch(m, c, n))
                self._sr_lay.addWidget(row)
        self._sr_lay.addStretch()

    # ── Launch ────────────────────────────────────────────────────
    def _launch(self, module_name, class_name, app_name):
        import importlib, inspect
        try:
            m   = importlib.import_module(module_name)
            cls = getattr(m, class_name)
            sig = inspect.signature(cls.__init__)
            params = list(sig.parameters.keys())
            # If constructor takes 'desktop' or 'parent' as first non-self param
            if len(params) > 1 and params[1] in ("desktop",):
                w = cls(self.desktop)
            else:
                w = cls()
            self.desktop.window_manager.open_window(w)
            _save_recent(app_name)
            self._refresh_recent()
        except Exception as ex:
            self.desktop.notify("❌ Launch Error", str(ex))
        self.hide()
        self._visible = False
        self._search.clear()
        self._stack.setCurrentIndex(0)

    # ── Power actions ─────────────────────────────────────────────
    def _lock(self):
        self.hide(); self._visible = False
        self.desktop._lock_screen()

    def _restart(self):
        self.hide()
        subprocess.run(["reboot"], check=False)

    def _shutdown(self):
        self.hide()
        subprocess.run(["shutdown", "-h", "now"], check=False)

    # ── Show / Hide ───────────────────────────────────────────────
    def toggle(self):
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self._reposition()
            self.show()
            self.raise_()
            self._search.setFocus()
            self._visible = True

    def _reposition(self):
        tb  = self.desktop.taskbar
        gp  = tb.mapToGlobal(QPoint(0, 0))
        self.move(gp.x() + 4, gp.y() - self.height() - 4)

    def focusOutEvent(self, e):
        # Hỏi xem focus rời đến đâu – nếu là widget con thì không ẩn
        pass
