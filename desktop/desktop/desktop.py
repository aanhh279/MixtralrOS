#!/usr/bin/env python3
"""
DesktopShell – MixtralOS (full-featured, Windows-style)
Features:
  - Wallpaper (custom + protected default)
  - Window snapping (Win+←/→/↑/↓)
  - Screenshot (PrtSc)
  - Lock screen
  - Action Center
  - Notification system
  - Theme engine
"""
import sys, json, os, datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QMenu, QStackedLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap, QPainter, QKeySequence

from taskbar       import Taskbar
from launcher      import Launcher
from notifications import NotificationCenter
from windows       import WindowManager
from desktop_icons import DesktopIconGrid
from action_center import ActionCenter
from lockscreen    import LockScreen

CONFIG_PATH = os.path.expanduser("~/.config/mixtralr/config.json")

# ── Default wallpaper resolution ─────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_WALLPAPER_CANDIDATES = [
    "/usr/share/mixtralr/picture/mixtralr-ui-d.png",
    os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "picture", "mixtralr-ui-d.png")),
]

def _resolve_default_wallpaper():
    for p in _DEFAULT_WALLPAPER_CANDIDATES:
        if os.path.isfile(p):
            return p
    return ""

DEFAULT_WALLPAPER = _resolve_default_wallpaper()

THEMES = {
    "neon-dark": {
        "bg": "#0d1117", "surface": "#161b22", "border": "#30363d",
        "text": "#e6edf3", "accent": "#58a6ff", "accent2": "#bc8cff",
        "button_hover": "#21262d", "taskbar_bg": "#010409",
    },
    "cyber-green": {
        "bg": "#030a03", "surface": "#0d1f0d", "border": "#1a4d1a",
        "text": "#a0f0a0", "accent": "#00ff41", "accent2": "#39ff14",
        "button_hover": "#0d2e0d", "taskbar_bg": "#050f05",
    },
    "midnight-purple": {
        "bg": "#0a0010", "surface": "#1a0030", "border": "#4a0080",
        "text": "#e8d5ff", "accent": "#bf7fff", "accent2": "#ff79c6",
        "button_hover": "#2a0050", "taskbar_bg": "#08000c",
    },
    "ocean-blue": {
        "bg": "#020c18", "surface": "#0a1929", "border": "#1e3a5a",
        "text": "#e0f0ff", "accent": "#00b4d8", "accent2": "#48cae4",
        "button_hover": "#0e2640", "taskbar_bg": "#010810",
    },
    "sunset-dark": {
        "bg": "#150a0a", "surface": "#1f0f0f", "border": "#4a1a1a",
        "text": "#ffe0d0", "accent": "#ff6b35", "accent2": "#ff9f1c",
        "button_hover": "#2f1515", "taskbar_bg": "#0d0606",
    },
}


class DesktopCanvas(QWidget):
    """Wallpaper layer"""
    def __init__(self, desktop):
        super().__init__()
        self.desktop      = desktop
        self._wallpaper   = None
        self._current_path = ""

    def set_wallpaper(self, path):
        resolved = self._resolve_wallpaper_path(path)
        if resolved == self._current_path:
            return
        if resolved and os.path.isfile(resolved):
            pix = QPixmap(resolved)
            if not pix.isNull():
                self._wallpaper    = pix
                self._current_path = resolved
                self.update()
                return
        self._wallpaper    = None
        self._current_path = ""
        self.update()

    @staticmethod
    def _resolve_wallpaper_path(path):
        if path and os.path.isfile(path):
            pix = QPixmap(path)
            if not pix.isNull():
                return path
        if DEFAULT_WALLPAPER and os.path.isfile(DEFAULT_WALLPAPER):
            return DEFAULT_WALLPAPER
        return ""

    def paintEvent(self, e):
        p = QPainter(self)
        if self._wallpaper:
            scaled = self._wallpaper.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            x = (self.width()  - scaled.width())  // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            p.fillRect(self.rect(), QColor(self.desktop.theme["bg"]))


class DesktopShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mixtralr Desktop")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self.config = self._load_config()
        self.theme  = THEMES.get(self.config.get("theme","neon-dark"), THEMES["neon-dark"])

        root  = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Desktop area ──────────────────────────────────────────
        desktop_area = QWidget()
        stack = QStackedLayout(desktop_area)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.canvas         = DesktopCanvas(self)
        self.window_manager = WindowManager(self)

        stack.addWidget(self.canvas)
        stack.addWidget(self.window_manager)
        stack.setCurrentIndex(1)

        # Icon grid overlay
        self.icon_grid = DesktopIconGrid(desktop_area)
        self.icon_grid._desktop = self
        self.icon_grid.setGeometry(0, 0, desktop_area.width() or 1280, desktop_area.height() or 720)
        self.icon_grid.init_icons()
        self.icon_grid.raise_()

        outer.addWidget(desktop_area, stretch=1)

        # ── Taskbar ───────────────────────────────────────────────
        self.taskbar = Taskbar(self)
        outer.addWidget(self.taskbar)

        # ── Overlay widgets ───────────────────────────────────────
        self.launcher      = Launcher(self)
        self.notifications = NotificationCenter(self)
        self.action_center = ActionCenter(self)

        # ── Theme + wallpaper ─────────────────────────────────────
        self.apply_theme()
        self.showFullScreen()

        # Screenshot folder
        self._screenshot_dir = os.path.expanduser("~/Pictures/Screenshots")
        os.makedirs(self._screenshot_dir, exist_ok=True)

        QTimer.singleShot(900, lambda: self.notify(
            "⚡ Welcome", "Mixtralr OS is ready. Press Win+S for search."))

    # ── Config ───────────────────────────────────────────────────
    def _load_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        default = {
            "theme": "neon-dark", "wallpaper": "",
            "font": "DejaVu Sans", "volume": 75, "brightness": 80,
        }
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w") as f:
                json.dump(default, f, indent=2)
            return default
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            for k, v in default.items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, OSError):
            return default

    def save_config(self, data):
        self.config.update(data)
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=2)
        except OSError as e:
            self.notify("❌ Config Error", str(e))
        self.apply_theme(data.get("theme"))

    # ── Theme ────────────────────────────────────────────────────
    def apply_theme(self, theme_name=None):
        if theme_name:
            self.config["theme"] = theme_name
        self.theme = THEMES.get(self.config.get("theme","neon-dark"), THEMES["neon-dark"])
        t = self.theme
        self.setStyleSheet(f"""
            QWidget {{
                background: {t['bg']};
                color: {t['text']};
                font-family: 'DejaVu Sans', sans-serif;
                font-size: 13px;
            }}
            QPushButton {{
                background: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 5px 14px;
            }}
            QPushButton:hover {{
                background: {t['button_hover']};
                border-color: {t['accent']};
                color: {t['accent']};
            }}
            QPushButton:pressed {{ background: {t['accent']}; color: {t['bg']}; }}
            QPushButton:checked  {{ background: {t['accent']}; color: {t['bg']};
                                    border-color: {t['accent']}; }}
            QLineEdit, QPlainTextEdit, QTextEdit {{
                background: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 4px 8px;
                selection-background-color: {t['accent']};
                selection-color: {t['bg']};
            }}
            QTreeView, QListView, QTableWidget {{
                background: {t['surface']};
                color: {t['text']};
                border: none;
                alternate-background-color: {t['bg']};
                outline: none;
                gridline-color: {t['border']};
            }}
            QTreeView::item:selected, QListView::item:selected {{
                background: {t['accent']}; color: {t['bg']};
            }}
            QTreeView::item:hover, QListView::item:hover {{
                background: {t['button_hover']};
            }}
            QHeaderView::section {{
                background: {t['surface']};
                color: {t['text']};
                border: none;
                border-right: 1px solid {t['border']};
                padding: 4px 8px;
            }}
            QMdiArea    {{ background: transparent; }}
            QMdiSubWindow {{
                background: {t['surface']};
                border: 1px solid {t['border']};
            }}
            QMdiSubWindow::title {{
                background: {t['taskbar_bg']};
                color: {t['accent']};
                padding: 3px;
            }}
            QScrollBar:vertical {{
                background: {t['surface']}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['border']}; border-radius: 4px; min-height: 20px;
            }}
            QScrollBar:horizontal {{
                background: {t['surface']}; height: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {t['border']}; border-radius: 4px; min-width: 20px;
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{ background: none; border: none; }}
            QMenu {{
                background: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 7px 28px; border-radius: 4px; margin: 1px 4px; }}
            QMenu::item:selected {{ background: {t['button_hover']}; color: {t['accent']}; }}
            QMenu::separator {{ background: {t['border']}; height: 1px; margin: 4px 8px; }}
            QLabel  {{ color: {t['text']}; background: transparent; }}
            QSplitter::handle {{ background: {t['border']}; }}
            QComboBox {{
                background: {t['surface']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {t['surface']}; color: {t['text']};
                border: 1px solid {t['border']};
                selection-background-color: {t['accent']}; selection-color: {t['bg']};
            }}
            QTabWidget::pane {{ border: 1px solid {t['border']}; }}
            QTabBar::tab {{
                background: {t['surface']}; color: {t['text']};
                padding: 6px 16px;
                border: 1px solid {t['border']};
                border-bottom: none; border-radius: 4px 4px 0 0;
            }}
            QTabBar::tab:selected {{ background: {t['button_hover']}; color: {t['accent']}; }}
            QProgressBar {{
                background: {t['surface']}; border: none;
                border-radius: 4px; height: 8px;
            }}
            QProgressBar::chunk {{ background: {t['accent']}; border-radius: 4px; }}
            QCheckBox {{ color: {t['text']}; }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {t['border']}; border-radius: 3px;
                background: {t['surface']};
            }}
            QCheckBox::indicator:checked {{
                background: {t['accent']}; border-color: {t['accent']};
            }}
            QSlider::groove:horizontal {{
                background: {t['border']}; height: 6px; border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {t['accent']}; width: 16px; height: 16px;
                border-radius: 8px; margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {t['accent']}; border-radius: 3px;
            }}
            QToolBar {{
                background: {t['surface']};
                border-bottom: 1px solid {t['border']};
                spacing: 4px; padding: 2px 6px;
            }}
            QStatusBar {{
                background: {t['taskbar_bg']};
                color: {t['text']};
                border-top: 1px solid {t['border']};
            }}
            QDialog {{
                background: {t['bg']};
                border: 1px solid {t['border']};
                border-radius: 8px;
            }}
        """)
        if hasattr(self, "canvas"):
            self.canvas.set_wallpaper(self.config.get("wallpaper", ""))
        if hasattr(self, "taskbar"):
            self.taskbar.refresh_style(t)

    # ── Notifications ─────────────────────────────────────────────
    def notify(self, title, text):
        self.notifications.push(title, text)
        # Update notification bell badge
        if hasattr(self, "taskbar"):
            self.taskbar._notif_badge += 1
            self.taskbar._notif_btn.setText("🔔")
            self.taskbar._notif_btn.setToolTip(
                f"Notifications ({self.taskbar._notif_badge} unread)")

    # ── Lock screen ───────────────────────────────────────────────
    def _lock_screen(self):
        lock = LockScreen(self, on_unlock=self._on_unlock)
        lock.show()
        lock.raise_()

    def _on_unlock(self):
        self.notify("🔓 Unlocked", "Welcome back!")
        if hasattr(self, "taskbar"):
            self.taskbar._notif_badge = 0
            self.taskbar._notif_btn.setToolTip("Notifications")

    # ── Screenshot ────────────────────────────────────────────────
    def _screenshot(self):
        screen = QApplication.primaryScreen()
        pix    = screen.grabWindow(0)
        ts     = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path   = os.path.join(self._screenshot_dir, f"screenshot_{ts}.png")
        if pix.save(path):
            self.notify("📸 Screenshot", f"Saved to:\n{path}")
        else:
            self.notify("❌ Screenshot", "Failed to save screenshot.")

    # ── Window snapping ───────────────────────────────────────────
    def _snap_active(self, mode):
        """Snap the focused MDI sub-window to half/full screen"""
        mdi = self.window_manager.mdi
        sub = mdi.activeSubWindow()
        if not sub: return

        mdi_w = mdi.width()
        mdi_h = mdi.height()

        if mode == "left":
            sub.showNormal()
            sub.setGeometry(0, 0, mdi_w // 2, mdi_h)
        elif mode == "right":
            sub.showNormal()
            sub.setGeometry(mdi_w // 2, 0, mdi_w // 2, mdi_h)
        elif mode == "maximize":
            sub.showMaximized()
        elif mode == "restore":
            sub.showNormal()
            sub.setGeometry(mdi_w//4, mdi_h//4, mdi_w//2, mdi_h//2)
        elif mode == "top-left":
            sub.showNormal()
            sub.setGeometry(0, 0, mdi_w//2, mdi_h//2)
        elif mode == "top-right":
            sub.showNormal()
            sub.setGeometry(mdi_w//2, 0, mdi_w//2, mdi_h//2)
        elif mode == "bottom-left":
            sub.showNormal()
            sub.setGeometry(0, mdi_h//2, mdi_w//2, mdi_h//2)
        elif mode == "bottom-right":
            sub.showNormal()
            sub.setGeometry(mdi_w//2, mdi_h//2, mdi_w//2, mdi_h//2)

    # ── Keyboard shortcuts ────────────────────────────────────────
    def keyPressEvent(self, e):
        key  = e.key()
        mods = e.modifiers()
        Win  = Qt.KeyboardModifier.MetaModifier
        Ctrl = Qt.KeyboardModifier.ControlModifier
        Alt  = Qt.KeyboardModifier.AltModifier

        # Win+← → snap left
        if mods & Win and key == Qt.Key.Key_Left:
            self._snap_active("left"); return
        # Win+→ → snap right
        if mods & Win and key == Qt.Key.Key_Right:
            self._snap_active("right"); return
        # Win+↑ → maximize
        if mods & Win and key == Qt.Key.Key_Up:
            self._snap_active("maximize"); return
        # Win+↓ → restore
        if mods & Win and key == Qt.Key.Key_Down:
            self._snap_active("restore"); return
        # Win+S → search (focus taskbar search)
        if mods & Win and key == Qt.Key.Key_S:
            self.taskbar._search.setFocus()
            self.taskbar._search.selectAll(); return
        # Win key alone or Ctrl+Escape → launcher
        if key == Qt.Key.Key_Super_L or (mods & Ctrl and key == Qt.Key.Key_Escape):
            self.launcher.toggle(); return
        # PrtSc → screenshot
        if key == Qt.Key.Key_Print:
            self._screenshot(); return
        # Ctrl+Alt+T → terminal
        if mods & Ctrl and mods & Alt and key == Qt.Key.Key_T:
            from terminal import MixtralrTerminal
            self.window_manager.open_window(MixtralrTerminal()); return
        # Win+L → lock
        if mods & Win and key == Qt.Key.Key_L:
            self._lock_screen(); return
        # Win+D → show/hide all windows (minimize all)
        if mods & Win and key == Qt.Key.Key_D:
            self._toggle_minimize_all(); return
        # Alt+F4 → close active window
        if mods & Alt and key == Qt.Key.Key_F4:
            sub = self.window_manager.mdi.activeSubWindow()
            if sub: sub.close(); return

        super().keyPressEvent(e)

    def _toggle_minimize_all(self):
        mdi  = self.window_manager.mdi
        subs = mdi.subWindowList()
        if not subs: return
        any_visible = any(not s.isMinimized() for s in subs)
        if any_visible:
            for s in subs: s.showMinimized()
        else:
            for s in subs: s.showNormal()

    # ── Resize ───────────────────────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "icon_grid") and self.icon_grid.parent():
            p = self.icon_grid.parent()
            self.icon_grid.setGeometry(0, 0, p.width(), p.height())
            self.icon_grid.raise_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w   = DesktopShell()
    w.show()
    app.exec()
