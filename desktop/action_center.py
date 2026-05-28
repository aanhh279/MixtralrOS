#!/usr/bin/env python3
"""Action Center – MixtralOS (quick settings, volume, notifications)"""
import os, json, subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient

CONFIG_PATH = os.path.expanduser("~/.config/mixtralr/config.json")

try:
    import psutil as _psutil; _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _save_cfg_key(key, val):
    try:
        d = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f: d = json.load(f)
        d[key] = val
        with open(CONFIG_PATH, "w") as f: json.dump(d, f, indent=2)
    except Exception: pass

def _load_cfg_key(key, default=None):
    try:
        with open(CONFIG_PATH) as f: d = json.load(f)
        return d.get(key, default)
    except Exception: return default


class ToggleButton(QPushButton):
    """Nút toggle ON/OFF với style đẹp"""
    def __init__(self, icon, label, cfg_key, default=False):
        super().__init__()
        self._icon    = icon
        self._label   = label
        self._cfg_key = cfg_key
        self._state   = _load_cfg_key(cfg_key, default)
        self.setFixedSize(100, 68)
        self.setCheckable(True)
        self.setChecked(self._state)
        self.clicked.connect(self._toggle)
        self._refresh_style()

    def _toggle(self):
        self._state = not self._state
        self.setChecked(self._state)
        _save_cfg_key(self._cfg_key, self._state)
        self._refresh_style()

    def _refresh_style(self):
        if self._state:
            self.setStyleSheet("""
                QPushButton{background:#1a4a9f;color:#ffffff;border:1px solid #2060cf;
                    border-radius:10px;text-align:center;}
                QPushButton:hover{background:#2060cf;}
            """)
        else:
            self.setStyleSheet("""
                QPushButton{background:#21262d;color:#8b949e;border:1px solid #30363d;
                    border-radius:10px;text-align:center;}
                QPushButton:hover{background:#30363d;color:#e6edf3;}
            """)
        self.setText(f"{self._icon}\n{self._label}")
        self.setFont(QFont("Segoe UI Emoji", 10))


class ActionCenter(QWidget):
    def __init__(self, desktop):
        super().__init__(desktop)
        self._desktop = desktop
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(340)
        self._visible = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Card
        self._card = QWidget()
        self._card.setObjectName("ACCard")
        self._card.setStyleSheet("""
            QWidget#ACCard{
                background: rgba(13,17,23,0.97);
                border: 1px solid #30363d;
                border-radius: 12px;
            }
        """)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(16, 14, 16, 16)
        card_lay.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr_lbl = QLabel("⚡ Quick Settings")
        hdr_lbl.setFont(QFont("DejaVu Sans", 12, QFont.Weight.Bold))
        hdr_lbl.setStyleSheet("color:#e6edf3; background:transparent;")

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setStyleSheet(
            "background:#21262d;color:#58a6ff;border:1px solid #30363d;border-radius:6px;"
        )
        settings_btn.clicked.connect(self._open_settings)
        settings_btn.setToolTip("Open Settings")

        hdr.addWidget(hdr_lbl)
        hdr.addStretch()
        hdr.addWidget(settings_btn)
        card_lay.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#30363d;"); card_lay.addWidget(sep)

        # Quick toggle grid
        grid_w = QWidget(); grid_w.setStyleSheet("background:transparent;")
        grid = QHBoxLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._wifi_btn = ToggleButton("🌐", "Network",    "quick_network", True)
        self._bt_btn   = ToggleButton("📶", "Bluetooth",  "quick_bt",      False)
        self._nm_btn   = ToggleButton("🌙", "Night Mode", "quick_night",   False)
        self._fs_btn   = ToggleButton("⛶",  "Full Screen","quick_fs",      False)
        for b in (self._wifi_btn, self._bt_btn, self._nm_btn, self._fs_btn):
            grid.addWidget(b)
        card_lay.addWidget(grid_w)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:#30363d;"); card_lay.addWidget(sep2)

        # Volume
        vol_hdr = QHBoxLayout()
        vol_icon = QLabel("🔊"); vol_icon.setFont(QFont("Segoe UI Emoji", 14))
        vol_icon.setStyleSheet("background:transparent;color:#e6edf3;")
        vol_lbl = QLabel("Volume"); vol_lbl.setStyleSheet("color:#e6edf3; background:transparent;")
        vol_lbl.setFont(QFont("DejaVu Sans", 11))
        self._vol_pct = QLabel("—%")
        self._vol_pct.setStyleSheet("color:#8b949e; background:transparent; font-size:10px;")
        vol_hdr.addWidget(vol_icon); vol_hdr.addWidget(vol_lbl)
        vol_hdr.addStretch(); vol_hdr.addWidget(self._vol_pct)
        card_lay.addLayout(vol_hdr)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        vol_saved = _load_cfg_key("volume", 75)
        self._vol_slider.setValue(vol_saved)
        self._vol_pct.setText(f"{vol_saved}%")
        self._vol_slider.setFixedHeight(20)
        self._vol_slider.setStyleSheet("""
            QSlider::groove:horizontal{background:#30363d;height:6px;border-radius:3px;}
            QSlider::handle:horizontal{background:#58a6ff;width:16px;height:16px;
                border-radius:8px;margin:-5px 0;}
            QSlider::sub-page:horizontal{background:#58a6ff;border-radius:3px;}
        """)
        self._vol_slider.valueChanged.connect(self._on_volume)
        card_lay.addWidget(self._vol_slider)

        # Brightness (visual only)
        br_hdr = QHBoxLayout()
        br_icon = QLabel("☀"); br_icon.setFont(QFont("Segoe UI Emoji", 14))
        br_icon.setStyleSheet("background:transparent;color:#e6edf3;")
        br_lbl = QLabel("Brightness"); br_lbl.setStyleSheet("color:#e6edf3;background:transparent;")
        br_lbl.setFont(QFont("DejaVu Sans", 11))
        self._br_pct = QLabel("—%")
        self._br_pct.setStyleSheet("color:#8b949e;background:transparent;font-size:10px;")
        br_hdr.addWidget(br_icon); br_hdr.addWidget(br_lbl)
        br_hdr.addStretch(); br_hdr.addWidget(self._br_pct)
        card_lay.addLayout(br_hdr)

        self._br_slider = QSlider(Qt.Orientation.Horizontal)
        self._br_slider.setRange(10, 100)
        br_saved = _load_cfg_key("brightness", 80)
        self._br_slider.setValue(br_saved)
        self._br_pct.setText(f"{br_saved}%")
        self._br_slider.setFixedHeight(20)
        self._br_slider.setStyleSheet("""
            QSlider::groove:horizontal{background:#30363d;height:6px;border-radius:3px;}
            QSlider::handle:horizontal{background:#ffa657;width:16px;height:16px;
                border-radius:8px;margin:-5px 0;}
            QSlider::sub-page:horizontal{background:#ffa657;border-radius:3px;}
        """)
        self._br_slider.valueChanged.connect(self._on_brightness)
        card_lay.addWidget(self._br_slider)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("background:#30363d;"); card_lay.addWidget(sep3)

        # System stats
        self._stats_lbl = QLabel("Loading system stats...")
        self._stats_lbl.setFont(QFont("Monospace", 9))
        self._stats_lbl.setStyleSheet("color:#8b949e; background:transparent;")
        self._stats_lbl.setWordWrap(True)
        card_lay.addWidget(self._stats_lbl)

        root.addWidget(self._card)

        # Stats timer
        self._stat_timer = QTimer(self)
        self._stat_timer.timeout.connect(self._update_stats)
        self._stat_timer.start(3000)
        self._update_stats()

        self.hide()

    def _on_volume(self, v):
        self._vol_pct.setText(f"{v}%")
        _save_cfg_key("volume", v)
        # Try to apply via pactl
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%"],
                           check=False, capture_output=True)
        except Exception: pass

    def _on_brightness(self, v):
        self._br_pct.setText(f"{v}%")
        _save_cfg_key("brightness", v)
        # Try to apply via xrandr or xbacklight
        try:
            br_f = v / 100
            subprocess.run(["xrandr", "--output", "LVDS-1", "--brightness", str(br_f)],
                           check=False, capture_output=True)
        except Exception: pass

    def _update_stats(self):
        if not _HAS_PSUTIL:
            self._stats_lbl.setText("psutil not available")
            return
        try:
            cpu  = _psutil.cpu_percent()
            mem  = _psutil.virtual_memory()
            self._stats_lbl.setText(
                f"CPU: {cpu:.1f}%   RAM: {mem.used//1024//1024}/{mem.total//1024//1024} MB"
            )
        except Exception:
            pass

    def _open_settings(self):
        from settings import MixtralrSettings
        self._desktop.window_manager.open_window(MixtralrSettings(self._desktop))
        self.hide()
        self._visible = False

    def toggle(self):
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self._reposition()
            self.show()
            self.raise_()
            self._visible = True

    def _reposition(self):
        tb = self._desktop.taskbar
        gpos = tb.mapToGlobal(QPoint(0, 0))
        screen_w = self._desktop.screen().geometry().width()
        x = screen_w - self.width() - 10
        y = gpos.y() - self.sizeHint().height() - 4
        self.move(x, max(4, y))

    def focusOutEvent(self, e):
        # Đừng ẩn khi click vào widget bên trong
        pass
