#!/usr/bin/env python3
"""
Taskbar – MixtralOS (Windows-style)
- Start button + active windows
- Search bar
- System tray: Network, Volume popup, Battery, Notification bell
- Clock with calendar popup
"""
import os, subprocess
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel,
    QFrame, QVBoxLayout, QSizePolicy, QLineEdit,
    QCalendarWidget, QSlider
)
from PyQt6.QtCore import (
    QTimer, QTime, Qt, QDate, QPoint, QPropertyAnimation,
    QEasingCurve, QRect, QSize
)
from PyQt6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QPen, QBrush,
    QLinearGradient, QIcon
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect

try:
    import psutil as _psutil; _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

PREVIEW_W = 230
PREVIEW_H = 145


# ── Window preview thumbnail ─────────────────────────────────────
class WindowPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(PREVIEW_W, PREVIEW_H + 28)
        self._pixmap = None
        self._title  = ""
        self._eff    = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._eff.setOpacity(0.0)
        self._anim   = QPropertyAnimation(self._eff, b"opacity", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_for(self, sub, pos):
        if sub.isMinimized() or not sub.isVisible():
            self.hide(); return
        w = sub.widget()
        if w is None: self.hide(); return
        pix = w.grab()
        self._pixmap = pix.scaled(
            PREVIEW_W - 14, PREVIEW_H - 6,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._title = sub.windowTitle()
        self.move(pos); self.show(); self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._eff.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.update()

    def fade_out(self):
        self._anim.stop()
        self._anim.setStartValue(self._eff.opacity())
        self._anim.setEndValue(0.0)
        try: self._anim.finished.disconnect()
        except Exception: pass
        self._anim.finished.connect(
            lambda: self.hide() if self._eff.opacity() < 0.05 else None)
        self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        p.setBrush(QBrush(QColor("#161b22")))
        p.setPen(QPen(QColor("#30363d"), 1))
        p.drawRoundedRect(r, 8, 8)
        tr = QRect(r.x(), r.y(), r.width(), 24)
        g  = QLinearGradient(tr.topLeft(), tr.bottomLeft())
        g.setColorAt(0, QColor("#1e2a3a")); g.setColorAt(1, QColor("#161b22"))
        p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(tr, 8, 8)
        p.drawRect(QRect(tr.x(), tr.y() + 10, tr.width(), 14))
        p.setPen(QColor("#58a6ff"))
        p.setFont(QFont("DejaVu Sans", 8, QFont.Weight.Bold))
        p.drawText(tr.adjusted(10, 0, -10, 0),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._title[:28])
        if self._pixmap:
            thumb_r = QRect(r.x() + 7, r.y() + 28, r.width() - 14, r.height() - 32)
            px_x = thumb_r.x() + (thumb_r.width()  - self._pixmap.width())  // 2
            px_y = thumb_r.y() + (thumb_r.height() - self._pixmap.height()) // 2
            p.drawPixmap(px_x, px_y, self._pixmap)
        else:
            p.setPen(QColor("#30363d"))
            p.drawText(r.adjusted(0, 24, 0, 0), Qt.AlignmentFlag.AlignCenter, "No preview")


# ── Taskbar window button ─────────────────────────────────────────
class TaskbarButton(QPushButton):
    def __init__(self, sub, preview: WindowPreview):
        super().__init__()
        self._sub     = sub
        self._preview = preview
        self._htimer  = QTimer(self)
        self._htimer.setSingleShot(True)
        self._htimer.timeout.connect(self._do_preview)
        self.setFixedHeight(30)
        self.setMinimumWidth(80)
        self.setMaximumWidth(160)
        self.setCheckable(True)
        self._refresh_label()

    def _refresh_label(self):
        title = self._sub.windowTitle() or "App"
        w = self._sub.widget()
        if w:
            ico = w.windowIcon()
            if ico and not ico.isNull():
                self.setIcon(ico)
                self.setIconSize(QSize(16, 16))
        self.setText(title[:18])

    def enterEvent(self, e):
        super().enterEvent(e)
        self._htimer.start(380)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._htimer.stop()
        self._preview.fade_out()

    def _do_preview(self):
        gp = self.mapToGlobal(QPoint(self.width() // 2, 0))
        px = gp.x() - PREVIEW_W // 2
        py = gp.y() - PREVIEW_H - 40
        self._preview.show_for(self._sub, QPoint(px, py))


# ── Calendar popup ────────────────────────────────────────────────
class CalendarPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        card = QWidget()
        card.setStyleSheet(
            "background:#161b22; border:1px solid #30363d; border-radius:10px;"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(8, 8, 8, 8)

        self._cal = QCalendarWidget()
        self._cal.setGridVisible(True)
        self._cal.setStyleSheet("""
            QCalendarWidget QAbstractItemView{background:#0d1117;color:#e6edf3;
                selection-background-color:#58a6ff;selection-color:#0d1117;}
            QCalendarWidget QWidget#qt_calendar_navigationbar{background:#161b22;}
            QCalendarWidget QToolButton{color:#58a6ff;background:transparent;font-weight:bold;}
            QCalendarWidget QMenu{background:#161b22;color:#e6edf3;}
            QCalendarWidget QSpinBox{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:4px;}
        """)
        card_lay.addWidget(self._cal)
        lay.addWidget(card)

    def show_at(self, gpos):
        self.adjustSize()
        x = gpos.x() - self.width() // 2
        y = gpos.y() - self.height() - 4
        self.move(x, y)
        self.show()
        self.raise_()


# ── Volume popup ──────────────────────────────────────────────────
class VolumePopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        card = QWidget()
        card.setStyleSheet(
            "background:#161b22; border:1px solid #30363d; border-radius:10px;"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 10, 12, 10)
        card_lay.setSpacing(6)

        top = QHBoxLayout()
        self._icon = QLabel("🔊"); self._icon.setFont(QFont("Segoe UI Emoji", 18))
        self._icon.setStyleSheet("background:transparent;")
        self._pct  = QLabel("75%"); self._pct.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
        self._pct.setStyleSheet("color:#58a6ff; background:transparent;")
        top.addWidget(self._icon); top.addStretch(); top.addWidget(self._pct)
        card_lay.addLayout(top)

        self._slider = QSlider(Qt.Orientation.Vertical)
        self._slider.setRange(0, 100)
        self._slider.setValue(75)
        self._slider.setFixedHeight(120)
        self._slider.setStyleSheet("""
            QSlider::groove:vertical{background:#30363d;width:8px;border-radius:4px;}
            QSlider::handle:vertical{background:#58a6ff;width:18px;height:18px;
                border-radius:9px;margin:0 -5px;}
            QSlider::add-page:vertical{background:#30363d;border-radius:4px;}
            QSlider::sub-page:vertical{background:#58a6ff;border-radius:4px;}
        """)
        self._slider.valueChanged.connect(self._on_change)
        card_lay.addWidget(self._slider, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(card)

    def _on_change(self, v):
        self._pct.setText(f"{v}%")
        if v == 0:   self._icon.setText("🔇")
        elif v < 40: self._icon.setText("🔉")
        else:        self._icon.setText("🔊")
        try:
            subprocess.run(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{v}%"],
                           check=False, capture_output=True)
        except Exception: pass

    def show_at(self, gpos):
        self.adjustSize()
        x = gpos.x() - self.width() // 2
        y = gpos.y() - self.height() - 4
        self.move(x, y)
        self.show()
        self.raise_()

    def set_value(self, v):
        self._slider.setValue(v)


# ── Network status icon ───────────────────────────────────────────
def _get_network_status():
    try:
        for iface in os.listdir("/sys/class/net"):
            if iface == "lo": continue
            state_file = f"/sys/class/net/{iface}/operstate"
            if os.path.exists(state_file):
                with open(state_file) as f:
                    if f.read().strip() == "up":
                        return True, iface
    except Exception: pass
    return False, ""


# ── Battery indicator ─────────────────────────────────────────────
def _get_battery():
    if not _HAS_PSUTIL: return None
    try:
        b = _psutil.sensors_battery()
        return b
    except Exception: return None


# ── Tray icon button ─────────────────────────────────────────────
class TrayBtn(QPushButton):
    def __init__(self, text, tooltip=""):
        super().__init__(text)
        self.setFixedSize(32, 32)
        self.setFont(QFont("Segoe UI Emoji", 13))
        self.setToolTip(tooltip)
        self.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#e6edf3;"
            "border-radius:6px;}"
            "QPushButton:hover{background:#21262d;}"
        )


# ── Main Taskbar ──────────────────────────────────────────────────
class Taskbar(QWidget):
    def __init__(self, desktop):
        super().__init__()
        self.desktop   = desktop
        self._win_btns = {}
        self._preview  = WindowPreview()
        self._cal_popup = CalendarPopup()
        self._vol_popup = VolumePopup()
        self._notif_badge = 0
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(4)

        # ── Start button ─────────────────────────────────────────
        self.start_btn = QPushButton("⚡ Start")
        self.start_btn.setFixedSize(90, 34)
        self.start_btn.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
        self.start_btn.clicked.connect(lambda: self.desktop.launcher.toggle())
        self.start_btn.setStyleSheet(
            "QPushButton{background:#1a4a9f;color:#ffffff;border:none;border-radius:7px;}"
            "QPushButton:hover{background:#2060cf;}"
            "QPushButton:pressed{background:#58a6ff;color:#0d1117;}"
        )

        sep0 = QFrame(); sep0.setFrameShape(QFrame.Shape.VLine)
        sep0.setFixedWidth(1); sep0.setStyleSheet("background:#30363d;")

        # ── Search bar ───────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search apps, files...")
        self._search.setFixedSize(200, 32)
        self._search.setStyleSheet(
            "background:#21262d; border:1px solid #30363d; border-radius:6px;"
            "padding:2px 10px; color:#e6edf3; font-size:11px;"
        )
        self._search.returnPressed.connect(self._do_search)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1); sep1.setStyleSheet("background:#30363d;")

        # ── Active window buttons area ────────────────────────────
        self._win_area   = QWidget()
        self._win_layout = QHBoxLayout(self._win_area)
        self._win_layout.setContentsMargins(0, 0, 0, 0)
        self._win_layout.setSpacing(3)
        self._win_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # ── System tray ──────────────────────────────────────────
        tray = QWidget()
        tray.setFixedHeight(40)
        tray_lay = QHBoxLayout(tray)
        tray_lay.setContentsMargins(4, 0, 4, 0)
        tray_lay.setSpacing(2)

        # Network
        self._net_btn = TrayBtn("🌐", "Network")
        self._net_btn.clicked.connect(self._show_network_info)
        tray_lay.addWidget(self._net_btn)

        # Volume
        self._vol_btn = TrayBtn("🔊", "Volume (click to adjust)")
        self._vol_btn.clicked.connect(self._toggle_volume)
        tray_lay.addWidget(self._vol_btn)

        # Battery
        self._bat_btn = TrayBtn("🔋", "Battery")
        tray_lay.addWidget(self._bat_btn)

        sep_tray = QFrame(); sep_tray.setFrameShape(QFrame.Shape.VLine)
        sep_tray.setFixedWidth(1); sep_tray.setStyleSheet("background:#30363d;")
        tray_lay.addWidget(sep_tray)

        # Notification bell
        self._notif_btn = TrayBtn("🔔", "Notifications / Action Center")
        self._notif_btn.clicked.connect(self._toggle_action_center)
        tray_lay.addWidget(self._notif_btn)

        sep_tray2 = QFrame(); sep_tray2.setFrameShape(QFrame.Shape.VLine)
        sep_tray2.setFixedWidth(1); sep_tray2.setStyleSheet("background:#30363d;")
        tray_lay.addWidget(sep_tray2)

        # Clock + date (clickable → calendar)
        clock_w = QWidget()
        clock_w.setCursor(Qt.CursorShape.PointingHandCursor)
        clock_w.setFixedWidth(76)
        clock_lay = QVBoxLayout(clock_w)
        clock_lay.setContentsMargins(2, 0, 2, 0)
        clock_lay.setSpacing(0)

        self.clock = QLabel()
        self.clock.setFont(QFont("DejaVu Sans", 11, QFont.Weight.Bold))
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.date_lbl = QLabel()
        self.date_lbl.setFont(QFont("DejaVu Sans", 8))
        self.date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        clock_lay.addWidget(self.clock)
        clock_lay.addWidget(self.date_lbl)
        tray_lay.addWidget(clock_w)

        # Click on clock_w → calendar
        clock_w.mousePressEvent = lambda e: self._toggle_calendar(clock_w)

        # ── Layout assembly ───────────────────────────────────────
        lay.addWidget(self.start_btn)
        lay.addWidget(sep0)
        lay.addWidget(self._search)
        lay.addWidget(sep1)
        lay.addWidget(self._win_area)
        lay.addStretch()
        lay.addWidget(tray)

        # ── Timers ────────────────────────────────────────────────
        ct = QTimer(self); ct.timeout.connect(self._tick); ct.start(1000); self._tick()
        wt = QTimer(self); wt.timeout.connect(self._refresh_windows); wt.start(400)
        st = QTimer(self); st.timeout.connect(self._update_tray);    st.start(5000)
        self._update_tray()

    # ── Clock ─────────────────────────────────────────────────────
    def _tick(self):
        self.clock.setText(QTime.currentTime().toString("HH:mm:ss"))
        self.date_lbl.setText(QDate.currentDate().toString("dd/MM/yy"))

    # ── Windows ──────────────────────────────────────────────────
    def _refresh_windows(self):
        mdi        = self.desktop.window_manager.mdi
        active_sub = mdi.activeSubWindow()
        seen       = set()
        for sub in mdi.subWindowList():
            wid = id(sub)
            seen.add(wid)
            if wid not in self._win_btns:
                btn = TaskbarButton(sub, self._preview)
                btn.clicked.connect(lambda _, s=sub: self._focus(s))
                self._win_layout.addWidget(btn)
                self._win_btns[wid] = btn
            b = self._win_btns[wid]
            b._refresh_label()
            b.setChecked(sub == active_sub and not sub.isMinimized())
        for wid in list(self._win_btns):
            if wid not in seen:
                b = self._win_btns.pop(wid)
                self._win_layout.removeWidget(b)
                b.deleteLater()

    def _focus(self, sub):
        mdi = self.desktop.window_manager.mdi
        if sub.isMinimized():
            sub.showNormal()
        mdi.setActiveSubWindow(sub)

    # ── System tray update ────────────────────────────────────────
    def _update_tray(self):
        # Network
        connected, iface = _get_network_status()
        self._net_btn.setText("🌐" if connected else "📵")
        self._net_btn.setToolTip(f"Network: {'Connected (' + iface + ')' if connected else 'Disconnected'}")

        # Battery
        bat = _get_battery()
        if bat:
            pct = int(bat.percent)
            plug = bat.power_plugged
            if plug:   icon = "🔌"
            elif pct > 80: icon = "🔋"
            elif pct > 40: icon = "🪫"
            else:          icon = "🪫"
            self._bat_btn.setText(icon)
            self._bat_btn.setToolTip(f"Battery: {pct}% {'(charging)' if plug else ''}")
        else:
            self._bat_btn.hide()

        # Volume from config
        import json
        try:
            with open(os.path.expanduser("~/.config/mixtralr/config.json")) as f:
                cfg = json.load(f)
            v = cfg.get("volume", 75)
            self._vol_btn.setText("🔇" if v == 0 else "🔉" if v < 40 else "🔊")
            self._vol_popup.set_value(v)
        except Exception:
            pass

    # ── Tray actions ─────────────────────────────────────────────
    def _toggle_volume(self):
        gp = self._vol_btn.mapToGlobal(QPoint(self._vol_btn.width()//2, 0))
        if self._vol_popup.isVisible():
            self._vol_popup.hide()
        else:
            self._vol_popup.show_at(gp)

    def _toggle_calendar(self, clock_w):
        gp = clock_w.mapToGlobal(QPoint(clock_w.width()//2, 0))
        if self._cal_popup.isVisible():
            self._cal_popup.hide()
        else:
            self._cal_popup.show_at(gp)

    def _toggle_action_center(self):
        self.desktop.action_center.toggle()

    def _show_network_info(self):
        connected, iface = _get_network_status()
        try:
            if _HAS_PSUTIL:
                addrs = _psutil.net_if_addrs()
                ip = ""
                for addr in addrs.get(iface, []):
                    if addr.family == 2:  # AF_INET
                        ip = addr.address
                        break
                msg = f"Interface: {iface}\nIP: {ip or '—'}\nStatus: {'Connected' if connected else 'Disconnected'}"
            else:
                msg = f"Interface: {iface or '—'}\nStatus: {'Connected' if connected else 'Disconnected'}"
        except Exception:
            msg = "Network info unavailable"
        self.desktop.notify("🌐 Network", msg)

    def _do_search(self):
        text = self._search.text().strip()
        if not text: return
        self._search.clear()
        # Search in active windows first
        mdi = self.desktop.window_manager.mdi
        for sub in mdi.subWindowList():
            if text.lower() in sub.windowTitle().lower():
                mdi.setActiveSubWindow(sub)
                sub.showNormal()
                return
        # Try to open known app
        app_map = {
            "terminal": ("terminal", "MixtralrTerminal"),
            "explorer":  ("explorer", "MixtralrExplorer"),
            "browser":   ("browser",  "MixtralrBrowser"),
            "settings":  ("settings", "MixtralrSettings"),
            "calc":      ("calculator","MixtralrCalculator"),
            "editor":    ("texteditor","MixtralrTextEditor"),
            "notepad":   ("texteditor","MixtralrTextEditor"),
            "task":      ("taskmanager","MixtralrTaskManager"),
            "image":     ("imageviewer","MixtralrImageViewer"),
        }
        for key, (mod, cls_name) in app_map.items():
            if key in text.lower():
                import importlib
                try:
                    m = importlib.import_module(mod)
                    cls = getattr(m, cls_name)
                    import inspect
                    sig = inspect.signature(cls.__init__)
                    params = list(sig.parameters.keys())
                    if len(params) > 1 and params[1] in ("desktop", "parent"):
                        w = cls(self.desktop)
                    else:
                        w = cls()
                    self.desktop.window_manager.open_window(w)
                    return
                except Exception: pass
        self.desktop.notify("🔍 Search", f"No results for: {text}")

    def refresh_style(self, t):
        self.setStyleSheet(f"""
            Taskbar {{
                background: {t['taskbar_bg']};
                border-top: 1px solid {t['border']};
            }}
            QPushButton {{
                background: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 2px 8px;
                text-align: left;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['accent']};
                background: {t['button_hover']};
            }}
            QPushButton:checked {{
                background: {t['accent']};
                color: {t['bg']};
                border-color: {t['accent']};
            }}
            QLabel {{
                color: {t['accent']};
                font-weight: bold;
                background: transparent;
            }}
            QFrame {{ background: {t['border']}; }}
            QLineEdit {{
                background: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 2px 8px;
            }}
        """)
        # Override start button separately
        self.start_btn.setStyleSheet(
            "QPushButton{background:#1a4a9f;color:#ffffff;border:none;border-radius:7px;}"
            "QPushButton:hover{background:#2060cf;}"
            "QPushButton:pressed{background:#58a6ff;color:#0d1117;}"
        )
