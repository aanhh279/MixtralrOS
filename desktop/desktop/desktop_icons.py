#!/usr/bin/env python3
"""
Desktop icon grid – MixtralOS
- Drag & drop reorder
- Right-click context menu
- Double-click to launch
- Icons: Terminal, Explorer, Browser, Text Editor, Calculator, Image Viewer, Task Manager, Settings, Recycle Bin
"""
import os, json
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGridLayout,
    QMenu, QMessageBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QPoint, QMimeData, QByteArray, QTimer
from PyQt6.QtGui import QFont, QDrag, QColor, QPainter, QBrush

CONFIG_PATH = os.path.expanduser("~/.config/mixtralr/icon_positions.json")

DEFAULT_ICONS = [
    {"emoji": "🖥",  "name": "Terminal",     "module": "terminal",    "cls": "MixtralrTerminal",    "row": 0, "col": 0},
    {"emoji": "📁",  "name": "Explorer",     "module": "explorer",    "cls": "MixtralrExplorer",    "row": 1, "col": 0},
    {"emoji": "🌐",  "name": "Browser",      "module": "browser",     "cls": "MixtralrBrowser",     "row": 2, "col": 0},
    {"emoji": "📝",  "name": "Text Editor",  "module": "texteditor",  "cls": "MixtralrTextEditor",  "row": 3, "col": 0},
    {"emoji": "🧮",  "name": "Calculator",   "module": "calculator",  "cls": "MixtralrCalculator",  "row": 4, "col": 0},
    {"emoji": "🖼",  "name": "Image Viewer", "module": "imageviewer", "cls": "MixtralrImageViewer", "row": 5, "col": 0},
    {"emoji": "📊",  "name": "Task Manager", "module": "taskmanager", "cls": "MixtralrTaskManager", "row": 6, "col": 0},
    {"emoji": "⚙",  "name": "Settings",     "module": "settings",    "cls": "MixtralrSettings",    "row": 7, "col": 0, "needs_desktop": True},
    {"emoji": "🗑",  "name": "Recycle Bin",  "module": None,          "cls": None,                  "row": 8, "col": 0, "special": "recycle"},
]


class DesktopIcon(QWidget):
    ICON_W = 76
    ICON_H = 80

    def __init__(self, icon_data: dict, grid):
        super().__init__(grid)
        self._data    = icon_data
        self._grid    = grid
        self._pressed = False
        self._drag_start = None

        self.setFixedSize(self.ICON_W, self.ICON_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._emoji_lbl = QLabel(icon_data["emoji"])
        self._emoji_lbl.setFont(QFont("Segoe UI Emoji", 28))
        self._emoji_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._emoji_lbl.setStyleSheet("background:transparent; border:none;")

        self._name_lbl = QLabel(icon_data["name"])
        self._name_lbl.setFont(QFont("DejaVu Sans", 8, QFont.Weight.Bold))
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet(
            "color:#e6edf3; background:transparent; border:none;"
        )

        lay.addWidget(self._emoji_lbl)
        lay.addWidget(self._name_lbl)

        self._selected = False
        self._apply_style()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(
                "QWidget{background:rgba(88,166,255,0.20);"
                "border:1px solid #58a6ff; border-radius:8px;}"
            )
        else:
            self.setStyleSheet(
                "QWidget{background:transparent; border:1px solid transparent;"
                "border-radius:8px;}"
            )

    def set_selected(self, v):
        self._selected = v
        self._apply_style()

    def enterEvent(self, e):
        if not self._selected:
            self.setStyleSheet(
                "QWidget{background:rgba(255,255,255,0.08);"
                "border:1px solid rgba(88,166,255,0.4); border-radius:8px;}"
            )

    def leaveEvent(self, e):
        self._apply_style()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed    = True
            self._drag_start = e.pos()
            self._grid._select_icon(self)
        elif e.button() == Qt.MouseButton.RightButton:
            self._grid._select_icon(self)
            self._show_context_menu(e.globalPos())

    def mouseReleaseEvent(self, e):
        self._pressed = False

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._launch()

    def mouseMoveEvent(self, e):
        if (self._pressed and self._drag_start and
                (e.pos() - self._drag_start).manhattanLength() > 8):
            self._start_drag()

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-desktop-icon",
                     QByteArray(self._data["name"].encode()))
        drag.setMimeData(mime)
        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        self._pressed = False
        drag.exec(Qt.DropAction.MoveAction)

    def _launch(self):
        data = self._data
        # Special icons
        if data.get("special") == "recycle":
            self._show_recycle()
            return
        if not data.get("module"): return

        import importlib, inspect
        try:
            m   = importlib.import_module(data["module"])
            cls = getattr(m, data["cls"])
            desktop = self._grid._desktop
            sig = inspect.signature(cls.__init__)
            params = list(sig.parameters.keys())
            if data.get("needs_desktop") or (len(params) > 1 and params[1] == "desktop"):
                w = cls(desktop)
            else:
                w = cls()
            desktop.window_manager.open_window(w)
        except Exception as ex:
            if self._grid._desktop:
                self._grid._desktop.notify("❌ Error", str(ex))

    def _show_recycle(self):
        trash = os.path.expanduser("~/.local/share/Trash/files")
        if not os.path.isdir(trash):
            if self._grid._desktop:
                self._grid._desktop.notify("🗑 Recycle Bin", "Bin is empty.")
            return
        files = os.listdir(trash)
        if not files:
            if self._grid._desktop:
                self._grid._desktop.notify("🗑 Recycle Bin", "Bin is empty.")
            return
        # Open explorer on trash folder
        import importlib
        try:
            m = importlib.import_module("explorer")
            w = m.MixtralrExplorer(path=trash)
            self._grid._desktop.window_manager.open_window(w)
        except Exception:
            if self._grid._desktop:
                self._grid._desktop.notify(
                    "🗑 Recycle Bin",
                    f"{len(files)} item(s) in trash:\n" + "\n".join(files[:10]))

    def _show_context_menu(self, gpos):
        menu = QMenu(self)
        menu.addAction(f"🚀  Open {self._data['name']}", self._launch)
        menu.addSeparator()
        menu.addAction("✏️  Rename", self._rename)
        menu.addAction("📌  Pin / Unpin", lambda: None)
        if self._data.get("special") != "recycle":
            menu.addSeparator()
            menu.addAction("❌  Remove from Desktop", self._remove)
        menu.exec(gpos)

    def _rename(self):
        new_name, ok = QInputDialog.getText(
            self, "Rename Icon", "New name:", text=self._data["name"])
        if ok and new_name.strip():
            self._data["name"] = new_name.strip()
            self._name_lbl.setText(new_name.strip())
            self._grid._save_positions()

    def _remove(self):
        r = QMessageBox.question(self, "Remove Icon",
            f"Remove '{self._data['name']}' from desktop?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._grid._remove_icon(self)


# ── Desktop icon grid ─────────────────────────────────────────────
class DesktopIconGrid(QWidget):
    COLS     = 1
    CELL_W   = 88
    CELL_H   = 90
    MARGIN_X = 16
    MARGIN_Y = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAcceptDrops(True)
        self._desktop   = None
        self._icons     = []
        self._selected  = None

    def init_icons(self):
        """Gọi sau khi self._desktop đã được gán"""
        data_list = self._load_positions() or [dict(d) for d in DEFAULT_ICONS]
        for d in data_list:
            ico = DesktopIcon(d, self)
            self._icons.append(ico)
        self._layout_icons()

    def _layout_icons(self):
        for i, ico in enumerate(self._icons):
            row = ico._data.get("row", i)
            col = ico._data.get("col", 0)
            x   = self.MARGIN_X + col * self.CELL_W
            y   = self.MARGIN_Y + row * self.CELL_H
            ico.move(x, y)
            ico.show()

    def _select_icon(self, icon):
        if self._selected and self._selected is not icon:
            self._selected.set_selected(False)
        self._selected = icon
        icon.set_selected(True)

    def mousePressEvent(self, e):
        if self._selected:
            self._selected.set_selected(False)
            self._selected = None

    # ── Context menu on empty desktop area ────────────────────────
    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.addAction("🔄  Reload Desktop",    lambda: self._desktop.apply_theme() if self._desktop else None)
        menu.addAction("📝  New Text File",      self._new_file)
        menu.addSeparator()
        menu.addAction("🖼  Change Wallpaper",   self._change_wallpaper)
        menu.addAction("⚙  Desktop Settings",   self._open_settings)
        menu.addSeparator()
        menu.addAction("📸  Screenshot",         lambda: self._desktop._screenshot() if self._desktop else None)
        menu.addAction("🖥  Terminal Here",      self._terminal_here)
        menu.exec(e.globalPos())

    def _new_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "New File", os.path.expanduser("~/Desktop/untitled.txt"),
            "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                open(path, "w").close()
            except Exception: pass

    def _change_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Wallpaper", os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path and self._desktop:
            self._desktop.save_config({"wallpaper": path})

    def _open_settings(self):
        if not self._desktop: return
        import importlib
        try:
            m = importlib.import_module("settings")
            w = m.MixtralrSettings(self._desktop)
            self._desktop.window_manager.open_window(w)
        except Exception: pass

    def _terminal_here(self):
        if not self._desktop: return
        import importlib
        try:
            m = importlib.import_module("terminal")
            w = m.MixtralrTerminal()
            w.cwd = os.path.expanduser("~/Desktop")
            self._desktop.window_manager.open_window(w)
        except Exception: pass

    # ── Drag & drop ───────────────────────────────────────────────
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-desktop-icon"):
            e.acceptProposedAction()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat("application/x-desktop-icon"):
            return
        name = e.mimeData().data("application/x-desktop-icon").data().decode()
        pos  = e.position().toPoint()
        col  = max(0, (pos.x() - self.MARGIN_X) // self.CELL_W)
        row  = max(0, (pos.y() - self.MARGIN_Y) // self.CELL_H)

        for ico in self._icons:
            if ico._data["name"] == name:
                ico._data["row"] = row
                ico._data["col"] = col
                ico.move(self.MARGIN_X + col * self.CELL_W,
                         self.MARGIN_Y + row * self.CELL_H)
                break
        self._save_positions()
        e.acceptProposedAction()

    def _remove_icon(self, icon):
        if icon in self._icons:
            self._icons.remove(icon)
            icon.deleteLater()
            self._save_positions()

    # ── Persistence ───────────────────────────────────────────────
    def _load_positions(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH) as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_positions(self):
        try:
            data = [dict(ico._data) for ico in self._icons]
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def paintEvent(self, e):
        pass  # transparent background – desktop canvas shows through
