#!/usr/bin/env python3
import sys
import os
import math
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient, QRadialGradient, QPen, QBrush


class ParticleWidget(QWidget):
    """Hiệu ứng hạt nền"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._particles = []
        self._tick = 0
        import random
        for _ in range(60):
            self._particles.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(0, 1),
                'vx': random.uniform(-0.0003, 0.0003),
                'vy': random.uniform(-0.0002, 0.0001),
                'r': random.uniform(1, 3),
                'a': random.uniform(0.1, 0.6),
            })
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(33)

    def _step(self):
        self._tick += 1
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['x'] < 0: p['x'] = 1
            if p['x'] > 1: p['x'] = 0
            if p['y'] < 0: p['y'] = 1
            if p['y'] > 1: p['y'] = 0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Gradient nền
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0,   QColor("#020510"))
        grad.setColorAt(0.5, QColor("#050d1f"))
        grad.setColorAt(1,   QColor("#010308"))
        p.fillRect(self.rect(), grad)

        # Particles
        for pt in self._particles:
            c = QColor("#58a6ff")
            c.setAlphaF(pt['a'])
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(
                QPoint(int(pt['x'] * w), int(pt['y'] * h)),
                int(pt['r']), int(pt['r'])
            )

        # Glow ở giữa
        cx, cy = w // 2, h // 2
        glow = QRadialGradient(cx, cy, 300)
        glow.setColorAt(0,   QColor(88, 166, 255, 18))
        glow.setColorAt(0.5, QColor(88, 166, 255, 6))
        glow.setColorAt(1,   QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 300, cy - 300, 600, 600)


class RingLoader(QWidget):
    """Vòng tròn loading quay"""
    def __init__(self, size=80, parent=None):
        super().__init__(parent)
        self._sz = size
        self._angle = 0
        self._progress = 0
        self.setFixedSize(size, size)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(16)

    def _step(self):
        self._angle = (self._angle + 4) % 360
        self.update()

    def set_progress(self, v):
        self._progress = v
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sz = self._sz
        margin = 8
        rect_inner = self.rect().adjusted(margin, margin, -margin, -margin)

        # Track
        pen = QPen(QColor("#1a2a4a"), 5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect_inner)

        # Arc xoay
        pen2 = QPen(QColor("#58a6ff"), 5)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        span = max(30, int(self._progress * 360 / 100)) if self._progress else 90
        start = (-self._angle + 90) * 16
        p.drawArc(rect_inner, start, -span * 16)

        # Percent text
        if self._progress > 0:
            p.setPen(QColor("#58a6ff"))
            p.setFont(QFont("DejaVu Sans", 9, QFont.Weight.Bold))
            p.drawText(rect_inner, Qt.AlignmentFlag.AlignCenter,
                       f"{self._progress}%")


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.showFullScreen()
        self._alpha = 0.0
        self._progress = 0
        self._status_text = "Initializing..."
        self._done = False

        # Background particles
        self._bg = ParticleWidget(self)
        self._bg.setGeometry(self.geometry())

        # Nội dung chính
        self._content = QWidget(self)

        layout = QVBoxLayout(self._content)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logo chữ
        self._logo = QLabel("⚡ Mixtralr")
        self._logo.setFont(QFont("DejaVu Sans", 52, QFont.Weight.Bold))
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setStyleSheet("color: #58a6ff; background: transparent;")

        self._subtitle = QLabel("Operating System")
        self._subtitle.setFont(QFont("DejaVu Sans", 16))
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setStyleSheet("color: #8b949e; background: transparent;")

        # Ring loader
        self._ring = RingLoader(72)

        # Status text
        self._status = QLabel(self._status_text)
        self._status.setFont(QFont("DejaVu Sans", 11))
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color: #8b949e; background: transparent;")

        # Version
        self._ver = QLabel("v1.0.0  •  Built with PyQt6")
        self._ver.setFont(QFont("DejaVu Sans", 9))
        self._ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ver.setStyleSheet("color: #30363d; background: transparent;")

        layout.addStretch(2)
        layout.addWidget(self._logo)
        layout.addWidget(self._subtitle)
        layout.addSpacing(30)
        layout.addWidget(self._ring, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)
        layout.addStretch(1)
        layout.addWidget(self._ver)
        layout.addSpacing(16)

        # Boot sequence
        self._steps = [
            (300,  10, "Loading kernel modules..."),
            (600,  25, "Starting system services..."),
            (900,  45, "Mounting filesystems..."),
            (1200, 60, "Initializing display server..."),
            (1500, 75, "Loading desktop environment..."),
            (1800, 90, "Starting Mixtralr Shell..."),
            (2100, 100, "Welcome ⚡"),
        ]

        for delay, pct, msg in self._steps:
            QTimer.singleShot(delay, lambda p=pct, m=msg: self._update(p, m))

        # Fade in
        QTimer.singleShot(100, self._fade_in)
        # Launch desktop sau 2.6s
        QTimer.singleShot(2600, self._launch)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg.setGeometry(0, 0, self.width(), self.height())
        self._content.setGeometry(0, 0, self.width(), self.height())

    def _fade_in(self):
        steps = 20
        self._fi_step = 0
        def step():
            self._fi_step += 1
            self._alpha = self._fi_step / steps
            # setWindowOpacity only works on top-level windows
            self.setWindowOpacity(self._alpha)
            if self._fi_step < steps:
                QTimer.singleShot(20, step)
            else:
                self.setWindowOpacity(1.0)
        step()

    def _update(self, progress, msg):
        if self._done:
            return
        self._progress = progress
        self._status_text = msg
        self._status.setText(msg)
        self._ring.set_progress(progress)
        if progress == 100:
            self._logo.setStyleSheet("color: #3fb950; background: transparent;")

    def _launch(self):
        self._done = True
        # Fade out rồi mở desktop
        steps = 15
        self._fo_step = 0
        def step():
            self._fo_step += 1
            opacity = 1.0 - self._fo_step / steps
            self.setWindowOpacity(opacity)
            if self._fo_step < steps:
                QTimer.singleShot(20, step)
            else:
                self._open_desktop()
        step()

    def _open_desktop(self):
        from desktop import DesktopShell
        self._desktop = DesktopShell()
        self._desktop.show()
        self.hide()  # hide thay close: tránh lastWindowClosed → app quit sớm

    def paintEvent(self, e):
        # Vẽ scan-line effect nhẹ lên trên background
        p = QPainter(self)
        p.setOpacity(0.03)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(1)
        p.setPen(pen)
        for y in range(0, self.height(), 4):
            p.drawLine(0, y, self.width(), y)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    sys.exit(app.exec())
