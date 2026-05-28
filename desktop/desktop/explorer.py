import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView,
    QListView, QSplitter, QLabel, QPushButton,
    QLineEdit, QMenu, QInputDialog, QMessageBox,
    QAbstractItemView, QFrame, QToolBar
)
from PyQt6.QtCore import Qt, QDir, QSize
from PyQt6.QtGui import QFont, QFileSystemModel, QIcon, QAction

try:
    from PyQt6.QtGui import QFileSystemModel
except ImportError:
    from PyQt6.QtWidgets import QFileSystemModel


class SidebarItem(QPushButton):
    def __init__(self, icon, label, path):
        super().__init__(f"  {icon}  {label}")
        self.path = path
        self.setFlat(True)
        self.setFixedHeight(32)
        self.setStyleSheet("text-align: left; border-radius: 4px;")


class MixtralrExplorer(QWidget):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowTitle("📁  File Explorer")
        self.setMinimumSize(780, 500)
        self._history = []
        self._hist_idx = -1
        self._start_path = path

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(44)
        toolbar.setObjectName("ExplorerToolbar")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(4)

        self.btn_back    = QPushButton("←")
        self.btn_forward = QPushButton("→")
        self.btn_up      = QPushButton("↑")
        for btn in (self.btn_back, self.btn_forward, self.btn_up):
            btn.setFixedSize(30, 30)

        self.addr_bar = QLineEdit()
        self.addr_bar.setFixedHeight(30)
        self.addr_bar.setFont(QFont("Monospace", 10))
        self.addr_bar.returnPressed.connect(self._go_addr)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Search")
        self.search_bar.setFixedSize(160, 30)
        self.search_bar.textChanged.connect(self._on_search)

        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_up.clicked.connect(self._go_up)

        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_forward)
        tb_layout.addWidget(self.btn_up)
        tb_layout.addWidget(self.addr_bar, stretch=1)
        tb_layout.addWidget(self.search_bar)

        root_layout.addWidget(toolbar)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(sep)

        # ── Body: sidebar + file view ─────────────────────
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(190)
        sidebar.setObjectName("Sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(4, 8, 4, 8)
        sb_layout.setSpacing(2)

        def section(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("DejaVu Sans", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #8b949e; padding: 8px 4px 4px 4px;")
            sb_layout.addWidget(lbl)

        home = os.path.expanduser('~')
        quick = [
            ("⭐", "Quick access", home),
            ("🖥",  "Desktop",     os.path.join(home, "Desktop")),
            ("📥", "Downloads",    os.path.join(home, "Downloads")),
            ("📄", "Documents",    os.path.join(home, "Documents")),
            ("🖼", "Pictures",     os.path.join(home, "Pictures")),
        ]
        section("Quick access")
        for icon, name, path in quick:
            btn = SidebarItem(icon, name, path)
            btn.clicked.connect(lambda _, p=path: self._navigate(p))
            sb_layout.addWidget(btn)

        section("Devices")
        drives = ["/", "/home", "/tmp"]
        drive_labels = [("💾", "Root (/)", "/"), ("🏠", "Home", "/home"), ("📦", "Temp", "/tmp")]
        for icon, name, path in drive_labels:
            btn = SidebarItem(icon, name, path)
            btn.clicked.connect(lambda _, p=path: self._navigate(p))
            sb_layout.addWidget(btn)

        sb_layout.addStretch()
        body.addWidget(sidebar)

        # File area
        file_area = QWidget()
        fa_layout = QVBoxLayout(file_area)
        fa_layout.setContentsMargins(0, 0, 0, 0)
        fa_layout.setSpacing(0)

        # View toggle bar
        view_bar = QWidget()
        view_bar.setFixedHeight(34)
        vb_layout = QHBoxLayout(view_bar)
        vb_layout.setContentsMargins(8, 2, 8, 2)
        vb_layout.setSpacing(4)

        self.btn_new_folder = QPushButton("📁 New Folder")
        self.btn_new_folder.setFixedHeight(26)
        self.btn_new_folder.clicked.connect(self._new_folder)

        self.btn_list  = QPushButton("☰")
        self.btn_grid  = QPushButton("⊞")
        self.btn_list.setFixedSize(26, 26)
        self.btn_grid.setFixedSize(26, 26)
        self.btn_list.clicked.connect(lambda: self._set_view("list"))
        self.btn_grid.clicked.connect(lambda: self._set_view("grid"))

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")

        vb_layout.addWidget(self.btn_new_folder)
        vb_layout.addStretch()
        vb_layout.addWidget(self.status_lbl)
        vb_layout.addWidget(self.btn_list)
        vb_layout.addWidget(self.btn_grid)
        fa_layout.addWidget(view_bar)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        fa_layout.addWidget(sep2)

        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.directoryLoaded.connect(self._on_dir_loaded)

        # List view
        self.list_view = QTreeView()
        self.list_view.setModel(self.model)
        self.list_view.setRootIndex(self.model.index(home))
        self.list_view.setColumnWidth(0, 280)
        self.list_view.setColumnWidth(1, 80)
        self.list_view.setColumnWidth(2, 100)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_view.doubleClicked.connect(self._on_double_click)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._context_menu)

        # Icon view
        self.icon_view = QListView()
        self.icon_view.setModel(self.model)
        self.icon_view.setRootIndex(self.model.index(home))
        self.icon_view.setViewMode(QListView.ViewMode.IconMode)
        self.icon_view.setIconSize(QSize(48, 48))
        self.icon_view.setGridSize(QSize(90, 80))
        self.icon_view.setWordWrap(True)
        self.icon_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.icon_view.doubleClicked.connect(self._on_double_click)
        self.icon_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.icon_view.customContextMenuRequested.connect(self._context_menu)
        self.icon_view.hide()

        fa_layout.addWidget(self.list_view, stretch=1)
        fa_layout.addWidget(self.icon_view, stretch=1)

        body.addWidget(file_area)
        body.setSizes([190, 600])
        root_layout.addWidget(body, stretch=1)

        # Status bar
        self.status_bar = QLabel("  Ready")
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet("color: #8b949e; font-size: 11px; padding-left: 8px;")
        root_layout.addWidget(self.status_bar)

        self._navigate(self._start_path if self._start_path and os.path.isdir(self._start_path) else home, push=False)

    def _current_view(self):
        return self.list_view if self.list_view.isVisible() else self.icon_view

    def _set_view(self, mode):
        if mode == "list":
            self.icon_view.hide()
            self.list_view.show()
        else:
            self.list_view.hide()
            self.icon_view.show()

    def _navigate(self, path, push=True):
        if not os.path.isdir(path):
            return
        if push:
            if self._hist_idx < len(self._history) - 1:
                self._history = self._history[:self._hist_idx + 1]
            self._history.append(path)
            self._hist_idx = len(self._history) - 1

        idx = self.model.index(path)
        self.list_view.setRootIndex(idx)
        self.icon_view.setRootIndex(idx)
        self.addr_bar.setText(path)
        self.btn_back.setEnabled(self._hist_idx > 0)
        self.btn_forward.setEnabled(self._hist_idx < len(self._history) - 1)
        self._update_status(path)

    def _update_status(self, path):
        try:
            items = os.listdir(path)
            self.status_bar.setText(f"  {len(items)} items")
        except:
            self.status_bar.setText("  —")

    def _on_dir_loaded(self, path):
        self._update_status(path)

    def _go_addr(self):
        self._navigate(self.addr_bar.text().strip())

    def _go_back(self):
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._navigate(self._history[self._hist_idx], push=False)

    def _go_forward(self):
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._navigate(self._history[self._hist_idx], push=False)

    def _go_up(self):
        cur = self.addr_bar.text()
        parent = os.path.dirname(cur)
        if parent and parent != cur:
            self._navigate(parent)

    def _on_double_click(self, idx):
        path = self.model.filePath(idx)
        if os.path.isdir(path):
            self._navigate(path)

    def _on_search(self, text):
        self.model.setNameFilters([f"*{text}*"] if text else [])
        self.model.setNameFilterDisables(False)

    def _selected_path(self, pos=None):
        v = self._current_view()
        idx = v.indexAt(pos) if pos else v.currentIndex()
        return self.model.filePath(idx) if idx.isValid() else None

    def _new_folder(self):
        cur = self.addr_bar.text()
        n, ok = QInputDialog.getText(self, 'New Folder', 'Folder name:')
        if ok and n:
            os.makedirs(os.path.join(cur, n), exist_ok=True)

    def _context_menu(self, pos):
        path = self._selected_path(pos)
        m = QMenu(self)
        a_open = m.addAction("📂  Open")
        m.addSeparator()
        a_copy = m.addAction("📋  Copy path")
        a_rn   = m.addAction("✏   Rename")
        a_del  = m.addAction("🗑   Delete")
        m.addSeparator()
        a_new  = m.addAction("📁  New Folder")
        a_file = m.addAction("📄  New File")

        if not path:
            for a in (a_open, a_copy, a_rn, a_del):
                a.setEnabled(False)

        a = m.exec(self._current_view().viewport().mapToGlobal(pos))

        if a == a_open and path and os.path.isdir(path):
            self._navigate(path)
        elif a == a_copy and path:
            QApplication.clipboard().setText(path)
        elif a == a_rn and path:
            n, ok = QInputDialog.getText(self, 'Rename',
                f'Rename "{os.path.basename(path)}" to:')
            if ok and n:
                os.rename(path, os.path.join(os.path.dirname(path), n))
        elif a == a_del and path:
            r = QMessageBox.question(self, 'Delete',
                f'Delete "{os.path.basename(path)}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                try:
                    shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
                except Exception as e:
                    QMessageBox.warning(self, 'Error', str(e))
        elif a == a_new:
            self._new_folder()
        elif a == a_file:
            cur = self.addr_bar.text()
            n, ok = QInputDialog.getText(self, 'New File', 'File name:')
            if ok and n:
                open(os.path.join(cur, n), 'a').close()
