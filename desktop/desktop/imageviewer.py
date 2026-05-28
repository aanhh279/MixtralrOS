#!/usr/bin/env python3
"""Image Viewer – MixtralOS (zoom, fit, next/prev, info)"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFileDialog, QSizePolicy, QSlider, QFrame
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QPixmap, QFont, QTransform, QWheelEvent, QKeyEvent

SUPPORTED = (".png",".jpg",".jpeg",".bmp",".webp",".gif",".tiff",".tif",".ico",".svg")


class ZoomableLabel(QLabel):
    """Label hỗ trợ zoom bằng mouse wheel và kéo bằng chuột"""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pix_orig   = None
        self._zoom       = 1.0
        self._pan_start  = None
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_pixmap(self, pix: QPixmap):
        self._pix_orig = pix
        self._zoom     = 1.0
        self._apply_zoom()

    def _apply_zoom(self):
        if not self._pix_orig: return
        w = int(self._pix_orig.width()  * self._zoom)
        h = int(self._pix_orig.height() * self._zoom)
        scaled = self._pix_orig.scaled(w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
        self.resize(max(scaled.width(), self.parentWidget().width() if self.parentWidget() else 400),
                    max(scaled.height(), self.parentWidget().height() if self.parentWidget() else 300))

    def zoom_in(self):
        if self._zoom < 8.0:
            self._zoom = min(8.0, self._zoom * 1.25)
            self._apply_zoom()

    def zoom_out(self):
        if self._zoom > 0.05:
            self._zoom = max(0.05, self._zoom / 1.25)
            self._apply_zoom()

    def fit_to_window(self):
        if not self._pix_orig: return
        parent = self.parentWidget()
        if not parent: return
        pw, ph = parent.width() - 20, parent.height() - 20
        ratio = min(pw / max(self._pix_orig.width(),1),
                    ph / max(self._pix_orig.height(),1))
        self._zoom = ratio
        self._apply_zoom()

    def reset_zoom(self):
        self._zoom = 1.0
        self._apply_zoom()

    def get_zoom(self):
        return self._zoom

    def wheelEvent(self, e: QWheelEvent):
        delta = e.angleDelta().y()
        if delta > 0: self.zoom_in()
        else:         self.zoom_out()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pan_start = e.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, e):
        self._pan_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, e):
        if self._pan_start:
            delta = e.pos() - self._pan_start
            self._pan_start = e.pos()
            area = self.parentWidget()
            if area:
                sb_h = area.horizontalScrollBar()
                sb_v = area.verticalScrollBar()
                sb_h.setValue(sb_h.value() - delta.x())
                sb_v.setValue(sb_v.value() - delta.y())


class MixtralrImageViewer(QWidget):
    def __init__(self, path=""):
        super().__init__()
        self.setWindowTitle("🖼  Image Viewer")
        self.setMinimumSize(640, 480)
        self._path      = ""
        self._folder    = []
        self._folder_idx = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────
        tb = QWidget()
        tb.setFixedHeight(40)
        tb.setStyleSheet("background:#161b22; border-bottom:1px solid #30363d;")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(6, 4, 6, 4)
        tb_lay.setSpacing(4)

        def btn(t, tip, slot, w=None):
            b = QPushButton(t); b.setToolTip(tip)
            b.setFixedHeight(28)
            if w: b.setFixedWidth(w)
            b.setFont(QFont("DejaVu Sans", 10))
            b.clicked.connect(slot)
            b.setStyleSheet(
                "QPushButton{background:#21262d;color:#e6edf3;border:1px solid #30363d;"
                "border-radius:4px;padding:2px 8px;}"
                "QPushButton:hover{border-color:#58a6ff;color:#58a6ff;}"
            )
            return b

        tb_lay.addWidget(btn("📂 Open",      "Open image",       self._open))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background:#30363d;"); tb_lay.addWidget(sep)
        tb_lay.addWidget(btn("◀",            "Previous image",   self._prev, 30))
        tb_lay.addWidget(btn("▶",            "Next image",       self._next, 30))
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("background:#30363d;"); tb_lay.addWidget(sep2)
        tb_lay.addWidget(btn("🔍+",          "Zoom in  (+)",     self._zoom_in,  40))
        tb_lay.addWidget(btn("🔍-",          "Zoom out (-)",     self._zoom_out, 40))
        tb_lay.addWidget(btn("⊞ Fit",        "Fit to window",    self._fit,      60))
        tb_lay.addWidget(btn("1:1",          "Actual size",      self._actual,   40))
        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("background:#30363d;"); tb_lay.addWidget(sep3)
        tb_lay.addWidget(btn("↺",            "Rotate left",      self._rot_left,  32))
        tb_lay.addWidget(btn("↻",            "Rotate right",     self._rot_right, 32))

        tb_lay.addStretch()
        self._info_lbl = QLabel("")
        self._info_lbl.setFont(QFont("DejaVu Sans", 9))
        self._info_lbl.setStyleSheet("color:#8b949e;")
        tb_lay.addWidget(self._info_lbl)
        root.addWidget(tb)

        # ── Scroll area with image ────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background:#0d1117; border:none;")
        self._scroll.setWidgetResizable(False)

        self._img_lbl = ZoomableLabel()
        self._scroll.setWidget(self._img_lbl)
        root.addWidget(self._scroll, stretch=1)

        # ── Status bar ────────────────────────────────────────────
        self._status = QLabel("Open an image to begin")
        self._status.setFixedHeight(20)
        self._status.setStyleSheet(
            "background:#0d1117; color:#8b949e; padding:2px 10px; font-size:10px;"
            "border-top:1px solid #30363d;"
        )
        root.addWidget(self._status)

        self._rotation = 0

        if path and os.path.isfile(path):
            self._load(path)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Load & navigation ─────────────────────────────────────────
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image",
            os.path.dirname(self._path) if self._path else os.path.expanduser("~"),
            f"Images (*{' *'.join(SUPPORTED)})"
        )
        if path:
            self._load(path)

    def _load(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            self._status.setText(f"❌ Cannot open: {path}")
            return
        self._path     = path
        self._rotation = 0
        self._pix_orig = pix
        self._img_lbl.set_pixmap(pix)
        self._img_lbl.fit_to_window()
        self._scan_folder(path)
        self._update_status()

    def _scan_folder(self, path):
        folder = os.path.dirname(path)
        try:
            files = sorted([
                os.path.join(folder, f) for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in SUPPORTED
            ])
        except OSError:
            files = [path]
        self._folder = files
        self._folder_idx = files.index(path) if path in files else 0

    def _prev(self):
        if not self._folder: return
        self._folder_idx = (self._folder_idx - 1) % len(self._folder)
        self._load(self._folder[self._folder_idx])

    def _next(self):
        if not self._folder: return
        self._folder_idx = (self._folder_idx + 1) % len(self._folder)
        self._load(self._folder[self._folder_idx])

    # ── Zoom & rotate ─────────────────────────────────────────────
    def _zoom_in(self):  self._img_lbl.zoom_in();       self._update_zoom()
    def _zoom_out(self): self._img_lbl.zoom_out();      self._update_zoom()
    def _fit(self):      self._img_lbl.fit_to_window(); self._update_zoom()
    def _actual(self):   self._img_lbl.reset_zoom();    self._update_zoom()

    def _rot_left(self):
        self._rotation = (self._rotation - 90) % 360
        self._apply_rotation()

    def _rot_right(self):
        self._rotation = (self._rotation + 90) % 360
        self._apply_rotation()

    def _apply_rotation(self):
        if not hasattr(self, "_pix_orig"): return
        t = QTransform().rotate(self._rotation)
        rotated = self._pix_orig.transformed(t, Qt.TransformationMode.SmoothTransformation)
        self._img_lbl.set_pixmap(rotated)
        self._img_lbl.fit_to_window()
        self._update_zoom()

    def _update_zoom(self):
        z = self._img_lbl.get_zoom()
        self._info_lbl.setText(f"{z*100:.0f}%")

    def _update_status(self):
        if not self._path: return
        pix = self._img_lbl._pix_orig
        if not pix: return
        try:
            size_kb = os.path.getsize(self._path) // 1024
        except OSError:
            size_kb = 0
        idx = self._folder_idx + 1
        total = len(self._folder)
        name = os.path.basename(self._path)
        self._status.setText(
            f"{name}  |  {pix.width()}×{pix.height()} px  |  {size_kb} KB  "
            f"|  {idx}/{total} in folder"
        )
        self.setWindowTitle(f"🖼  {name}")
        self._info_lbl.setText(f"{self._img_lbl.get_zoom()*100:.0f}%")

    # ── Keyboard shortcuts ────────────────────────────────────────
    def keyPressEvent(self, e: QKeyEvent):
        key = e.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Space): self._next()
        elif key == Qt.Key.Key_Left:                    self._prev()
        elif key == Qt.Key.Key_Plus:                    self._zoom_in()
        elif key == Qt.Key.Key_Minus:                   self._zoom_out()
        elif key == Qt.Key.Key_F:                       self._fit()
        elif key == Qt.Key.Key_1:                       self._actual()
        else: super().keyPressEvent(e)
