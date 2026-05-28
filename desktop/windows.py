#!/usr/bin/env python3
"""
WindowManager – MixtralOS
- QMdiArea với title bar đẹp (icon, tên window không dùng icon mặc định Qt)
- Hỗ trợ setWindowTitle + setWindowIcon từ child widget
"""
from PyQt6.QtWidgets import QWidget, QMdiArea, QMdiSubWindow, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor


def _make_emoji_icon(emoji: str, size: int = 32) -> QIcon:
    """Tạo QIcon từ emoji để dùng làm window icon"""
    from PyQt6.QtGui import QPainter, QFont
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setFont(QFont("Segoe UI Emoji", int(size * 0.6)))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    p.end()
    return QIcon(pix)


# Map tên class → emoji icon
_WINDOW_ICONS = {
    "MixtralrTerminal": ("🖥",  "Terminal"),
    "MixtralrExplorer": ("📁",  "Explorer"),
    "MixtralrBrowser":  ("🌐",  "Browser"),
    "MixtralrSettings": ("⚙",   "Settings"),
}


class WindowManager(QWidget):
    def __init__(self, desktop, parent=None):
        super().__init__(parent)
        self.desktop = desktop
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        self.mdi = QMdiArea()
        self.mdi.setBackground(Qt.GlobalColor.transparent)
        self.mdi.setViewMode(QMdiArea.ViewMode.SubWindowView)
        l.addWidget(self.mdi)

    def open_window(self, child) -> QMdiSubWindow:
        sub = QMdiSubWindow()
        sub.setWidget(child)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Lấy title + icon đẹp từ registry
        cls_name = type(child).__name__
        if cls_name in _WINDOW_ICONS:
            emoji, label = _WINDOW_ICONS[cls_name]
            title = label
            ico   = _make_emoji_icon(emoji)
        else:
            title = child.windowTitle() or cls_name
            ico   = child.windowIcon()

        sub.setWindowTitle(title)
        if ico and not ico.isNull():
            sub.setWindowIcon(ico)

        # Kích thước mặc định
        sub.resize(820, 560)

        self.mdi.addSubWindow(sub)
        sub.show()
        self.mdi.setActiveSubWindow(sub)
        return sub
