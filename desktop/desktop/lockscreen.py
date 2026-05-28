#!/usr/bin/env python3
"""
Lock Screen – MixtralOS
Tài khoản truy cập:
  1. Tài khoản người dùng: username/password lưu trong config.json
  2. Tài khoản mặc định KHÔNG XOÁ ĐƯỢC: admin / admin
     → dùng khi quên mật khẩu hoặc nhập sai nhiều lần
"""
import os, json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton
)
from PyQt6.QtCore import (
    Qt, QTimer, QTime, QDate,
    QPropertyAnimation, QEasingCurve, QPoint
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont,
    QLinearGradient, QRadialGradient, QBrush, QPen, QKeyEvent
)

CONFIG_PATH    = os.path.expanduser("~/.config/mixtralr/config.json")
_DEFAULT_USER  = "mixtralr"
_DEFAULT_PASS  = ""          # không đặt mật khẩu → Enter thẳng

# ── Tài khoản admin mặc định, KHÔNG THỂ XOÁ ──────────────────────
_ADMIN_USER = "admin"
_ADMIN_PASS = "admin"
# ─────────────────────────────────────────────────────────────────

_MAX_FAIL_SHOW_HINT = 3      # Sau N lần sai → gợi ý tài khoản admin


def _load_lock_cfg():
    """Trả về (password, username) từ config. Nếu lỗi dùng default."""
    try:
        with open(CONFIG_PATH) as f:
            d = json.load(f)
        return d.get("lock_password", _DEFAULT_PASS), d.get("username", _DEFAULT_USER)
    except Exception:
        return _DEFAULT_PASS, _DEFAULT_USER


def _check_credentials(username_input: str, password_input: str) -> tuple[bool, str]:
    """
    Kiểm tra thông tin đăng nhập.
    Trả về (success: bool, role: str)
    role = 'admin' | 'user'
    """
    # 1. Tài khoản admin mặc định – luôn hoạt động
    if username_input.strip() == _ADMIN_USER and password_input == _ADMIN_PASS:
        return True, "admin"

    # 2. Tài khoản người dùng từ config
    saved_pw, saved_user = _load_lock_cfg()
    # username khớp hoặc trống (single-user mode)
    user_match = (saved_user == "" or
                  username_input.strip() == "" or
                  username_input.strip() == saved_user)
    # password khớp hoặc không có mật khẩu
    pass_match = (saved_pw == "" or password_input == saved_pw)

    if user_match and pass_match:
        return True, "user"

    return False, ""


class LockScreen(QWidget):
    def __init__(self, desktop, on_unlock=None):
        super().__init__(desktop)
        self._desktop    = desktop
        self._on_unlock  = on_unlock
        self._attempts   = 0
        self._hint_shown = False

        self.setGeometry(desktop.geometry())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grabKeyboard()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Clock ─────────────────────────────────────────────────
        clock_wrap = QVBoxLayout()
        clock_wrap.setSpacing(4)
        clock_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._clock_lbl = QLabel()
        self._clock_lbl.setFont(QFont("DejaVu Sans", 60, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet("color: rgba(255,255,255,0.85); background:transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._date_lbl = QLabel()
        self._date_lbl.setFont(QFont("DejaVu Sans", 15))
        self._date_lbl.setStyleSheet("color: rgba(255,255,255,0.50); background:transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        clock_wrap.addWidget(self._clock_lbl)
        clock_wrap.addWidget(self._date_lbl)
        root.addLayout(clock_wrap)
        root.addSpacing(32)

        # ── Login card ────────────────────────────────────────────
        card = QWidget()
        card.setFixedWidth(380)
        card.setStyleSheet(
            "background: rgba(13,17,23,0.93);"
            "border: 1px solid #30363d;"
            "border-radius: 18px;"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(36, 30, 36, 30)
        card_lay.setSpacing(12)
        card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Avatar
        ava = QLabel("👤")
        ava.setFont(QFont("Segoe UI Emoji", 46))
        ava.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ava.setStyleSheet("background:transparent; border:none;")
        card_lay.addWidget(ava)

        # Displayed username
        _, username = _load_lock_cfg()
        self._user_lbl = QLabel(username or _DEFAULT_USER)
        self._user_lbl.setFont(QFont("DejaVu Sans", 14, QFont.Weight.Bold))
        self._user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._user_lbl.setStyleSheet("color:#e6edf3; background:transparent; border:none;")
        card_lay.addWidget(self._user_lbl)

        card_lay.addSpacing(4)

        # Username input (ẩn mặc định – hiện khi cần admin)
        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText("Username")
        self._user_input.setFixedHeight(38)
        self._user_input.setStyleSheet(self._field_style())
        self._user_input.setVisible(False)   # ẩn cho đến khi nhập sai nhiều lần
        self._user_input.returnPressed.connect(lambda: self._pw.setFocus())
        card_lay.addWidget(self._user_input)

        # Password field
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("🔒  Mật khẩu (hoặc nhấn Enter)")
        self._pw.setFixedHeight(40)
        self._pw.setStyleSheet(self._field_style())
        self._pw.returnPressed.connect(self._try_unlock)
        card_lay.addWidget(self._pw)

        # Error / hint label
        self._err = QLabel("")
        self._err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._err.setWordWrap(True)
        self._err.setStyleSheet(
            "color:#f85149; background:transparent; border:none; font-size:11px;")
        self._err.setFixedHeight(36)
        card_lay.addWidget(self._err)

        # Unlock button
        unlock_btn = QPushButton("🔓  Mở khoá")
        unlock_btn.setFixedHeight(40)
        unlock_btn.setFont(QFont("DejaVu Sans", 11, QFont.Weight.Bold))
        unlock_btn.clicked.connect(self._try_unlock)
        unlock_btn.setStyleSheet(
            "QPushButton{background:#1a4a9f;color:#ffffff;"
            "border:none;border-radius:9px;}"
            "QPushButton:hover{background:#2060cf;}"
            "QPushButton:pressed{background:#58a6ff;color:#0d1117;}"
        )
        card_lay.addWidget(unlock_btn)

        # Hint link (ẩn, hiện sau N lần sai)
        self._hint_lbl = QLabel(
            "💡 Quên mật khẩu? Dùng: <b>admin</b> / <b>admin</b>"
        )
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_lbl.setStyleSheet(
            "color:#8b949e; background:transparent; border:none; font-size:11px;")
        self._hint_lbl.setVisible(False)
        card_lay.addWidget(self._hint_lbl)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch()

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()
        self._pw.setFocus()

    # ── Styles ────────────────────────────────────────────────────
    @staticmethod
    def _field_style() -> str:
        return (
            "background:#21262d; border:1px solid #30363d; border-radius:9px;"
            "padding:6px 14px; color:#e6edf3; font-size:13px;"
            "selection-background-color:#58a6ff;"
        )

    # ── Clock ─────────────────────────────────────────────────────
    def _tick(self):
        self._clock_lbl.setText(QTime.currentTime().toString("HH:mm"))
        days = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
        d = QDate.currentDate()
        self._date_lbl.setText(
            f"{days[d.dayOfWeek()-1]}, {d.toString('dd/MM/yyyy')}"
        )

    # ── Auth ──────────────────────────────────────────────────────
    def _try_unlock(self):
        # Lấy username: nếu field ẩn thì dùng label username
        if self._user_input.isVisible():
            uname = self._user_input.text()
        else:
            _, uname = _load_lock_cfg()
            if not uname:
                uname = _DEFAULT_USER

        pw_input = self._pw.text()
        success, role = _check_credentials(uname, pw_input)

        if success:
            if role == "admin":
                # Thông báo ngắn rồi mở khoá
                self._err.setStyleSheet(
                    "color:#3fb950; background:transparent; border:none; font-size:11px;")
                self._err.setText("✅ Đăng nhập với quyền Admin")
                QTimer.singleShot(700, self._unlock)
            else:
                self._unlock()
        else:
            self._attempts += 1
            self._pw.clear()
            msg = f"❌ Sai mật khẩu. (Lần {self._attempts})"
            self._err.setStyleSheet(
                "color:#f85149; background:transparent; border:none; font-size:11px;")
            self._err.setText(msg)
            self._shake(self._pw)

            # Sau N lần sai: hiện gợi ý admin + bật username field
            if self._attempts >= _MAX_FAIL_SHOW_HINT and not self._hint_shown:
                self._hint_shown = True
                self._hint_lbl.setVisible(True)
                self._user_input.setVisible(True)
                self._user_input.setPlaceholderText("Username (vd: admin)")
                self._user_lbl.setText("Nhập tài khoản khác:")
                self._user_lbl.setStyleSheet(
                    "color:#8b949e; background:transparent; border:none; font-size:12px;")
                self._user_input.setFocus()

            QTimer.singleShot(3500, lambda: self._err.setText(""))

    def _shake(self, widget):
        """Hiệu ứng rung widget khi sai mật khẩu"""
        anim = QPropertyAnimation(widget, b"pos", self)
        anim.setDuration(320)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        pos = widget.pos()
        anim.setKeyValueAt(0,   pos)
        anim.setKeyValueAt(0.15, QPoint(pos.x() - 10, pos.y()))
        anim.setKeyValueAt(0.35, QPoint(pos.x() + 10, pos.y()))
        anim.setKeyValueAt(0.55, QPoint(pos.x() - 6,  pos.y()))
        anim.setKeyValueAt(0.75, QPoint(pos.x() + 6,  pos.y()))
        anim.setKeyValueAt(0.90, QPoint(pos.x() - 2,  pos.y()))
        anim.setKeyValueAt(1.0,  pos)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _unlock(self):
        self._timer.stop()
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if self._on_unlock:
            self._on_unlock()
        self.hide()
        self.deleteLater()

    # ── Paint ─────────────────────────────────────────────────────
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0,   QColor("#020510"))
        grad.setColorAt(0.5, QColor("#050d1f"))
        grad.setColorAt(1,   QColor("#0a0320"))
        p.fillRect(self.rect(), QBrush(grad))
        # Glow nhẹ giữa màn hình
        cx, cy = self.width() // 2, self.height() // 2
        glow = QRadialGradient(cx, cy, 400)
        glow.setColorAt(0,   QColor(88, 166, 255, 12))
        glow.setColorAt(0.6, QColor(88, 166, 255, 4))
        glow.setColorAt(1,   QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 400, cy - 400, 800, 800)
        # Scanlines nhẹ
        pen = QPen(QColor(255, 255, 255, 5))
        pen.setWidth(1)
        p.setPen(pen)
        for y in range(0, self.height(), 4):
            p.drawLine(0, y, self.width(), y)

    # ── Key / Resize ──────────────────────────────────────────────
    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Escape:
            pass   # không cho thoát
        else:
            super().keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._desktop:
            self.setGeometry(self._desktop.geometry())
