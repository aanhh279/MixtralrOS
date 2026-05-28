import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTabWidget, QTabBar, QLabel, QProgressBar,
    QMenu, QDialog, QListWidget, QListWidgetItem, QSplitter,
    QFrame
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QAction

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


HOME_URL = "https://www.google.com"

BOOKMARKS_FILE = os.path.expanduser("~/.config/mixtralr/bookmarks.txt")

DEFAULT_BOOKMARKS = [
    ("Google",     "https://www.google.com"),
    ("Wikipedia",  "https://www.wikipedia.org"),
    ("YouTube",    "https://www.youtube.com"),
    ("GitHub",     "https://www.github.com"),
    ("DuckDuckGo", "https://duckduckgo.com"),
]


def load_bookmarks():
    if not os.path.exists(BOOKMARKS_FILE):
        os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
        with open(BOOKMARKS_FILE, "w") as f:
            for name, url in DEFAULT_BOOKMARKS:
                f.write(f"{name}|{url}\n")
    bms = []
    with open(BOOKMARKS_FILE) as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                name, url = line.split("|", 1)
                bms.append((name.strip(), url.strip()))
    return bms


def save_bookmarks(bms):
    os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
    with open(BOOKMARKS_FILE, "w") as f:
        for name, url in bms:
            f.write(f"{name}|{url}\n")


class NoWebView(QWidget):
    """Fallback nếu QtWebEngine không có"""
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(
            "⚠  PyQt6-WebEngine not installed.\n\n"
            "Install it with:\n"
            "pip install PyQt6-WebEngine\n\n"
            "or on Debian/Ubuntu:\n"
            "apt install python3-pyqt6.qtwebengine"
        )
        lbl.setFont(QFont("DejaVu Sans", 13))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #f38ba8;")
        l.addWidget(lbl)


class BrowserTab(QWidget):
    """Một tab trình duyệt"""
    title_changed = pyqtSignal(str)
    url_changed   = pyqtSignal(str)
    load_progress = pyqtSignal(int)
    favicon_changed = pyqtSignal(object)

    def __init__(self, url=HOME_URL):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if WEB_AVAILABLE:
            self.view = QWebEngineView()
            # Bật JavaScript, media, etc.
            settings = self.view.settings()
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

            self.view.titleChanged.connect(self.title_changed)
            self.view.urlChanged.connect(
                lambda u: self.url_changed.emit(u.toString()))
            self.view.loadProgress.connect(self.load_progress)
            self.view.iconChanged.connect(self.favicon_changed)
            self.view.load(QUrl(url))
            layout.addWidget(self.view)
        else:
            self.view = None
            layout.addWidget(NoWebView())

    def load(self, url):
        if self.view:
            if not url.startswith("http"):
                url = "https://" + url
            self.view.load(QUrl(url))

    def back(self):
        if self.view: self.view.back()

    def forward(self):
        if self.view: self.view.forward()

    def reload(self):
        if self.view: self.view.reload()

    def stop(self):
        if self.view: self.view.stop()

    def current_url(self):
        if self.view: return self.view.url().toString()
        return ""

    def current_title(self):
        if self.view: return self.view.title()
        return "New Tab"


class BookmarkPanel(QWidget):
    go_url = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(6)

        title = QLabel("⭐  Bookmarks")
        title.setFont(QFont("DejaVu Sans", 11, QFont.Weight.Bold))
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(
            lambda item: self.go_url.emit(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.list)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("＋ Add")
        self.btn_del = QPushButton("🗑")
        self.btn_del.setFixedWidth(34)
        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._delete)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_del)
        layout.addLayout(btn_row)

        self._bookmarks = load_bookmarks()
        self._refresh()
        self._get_url = lambda: ""   # sẽ được set dari luar

    def _refresh(self):
        self.list.clear()
        for name, url in self._bookmarks:
            item = QListWidgetItem(f"⭐  {name}")
            item.setData(Qt.ItemDataRole.UserRole, url)
            item.setToolTip(url)
            self.list.addItem(item)

    def _add(self):
        url = self._get_url()
        if not url:
            return
        name = url.split("//")[-1].split("/")[0]
        self._bookmarks.append((name, url))
        save_bookmarks(self._bookmarks)
        self._refresh()

    def _delete(self):
        row = self.list.currentRow()
        if row >= 0:
            self._bookmarks.pop(row)
            save_bookmarks(self._bookmarks)
            self._refresh()


class MixtralrBrowser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌐  Mixtralr Browser")
        self.setMinimumSize(1000, 650)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Toolbar ──────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(46)
        toolbar.setObjectName("BrowserToolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(6, 4, 6, 4)
        tb.setSpacing(4)

        self.btn_back    = QPushButton("←")
        self.btn_forward = QPushButton("→")
        self.btn_reload  = QPushButton("↺")
        self.btn_home    = QPushButton("🏠")
        self.btn_bm      = QPushButton("⭐")
        self.btn_new_tab = QPushButton("＋")

        for btn in (self.btn_back, self.btn_forward,
                    self.btn_reload, self.btn_home,
                    self.btn_bm, self.btn_new_tab):
            btn.setFixedSize(32, 32)

        self.addr_bar = QLineEdit()
        self.addr_bar.setFixedHeight(32)
        self.addr_bar.setPlaceholderText("Search or enter URL...")
        self.addr_bar.setFont(QFont("DejaVu Sans", 11))
        self.addr_bar.returnPressed.connect(self._go)

        self.btn_back.clicked.connect(self._back)
        self.btn_forward.clicked.connect(self._forward)
        self.btn_reload.clicked.connect(self._reload)
        self.btn_home.clicked.connect(self._home)
        self.btn_bm.clicked.connect(self._toggle_bookmarks)
        self.btn_new_tab.clicked.connect(lambda: self._new_tab())

        tb.addWidget(self.btn_back)
        tb.addWidget(self.btn_forward)
        tb.addWidget(self.btn_reload)
        tb.addWidget(self.btn_home)
        tb.addWidget(self.addr_bar, stretch=1)
        tb.addWidget(self.btn_bm)
        tb.addWidget(self.btn_new_tab)
        main.addWidget(toolbar)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.hide()
        main.addWidget(self.progress)

        # Body: bookmark panel + tabs
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)

        # Bookmark panel
        self.bm_panel = BookmarkPanel()
        self.bm_panel.go_url.connect(self._load_url)
        self.bm_panel.hide()
        body.addWidget(self.bm_panel)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_change)
        body.addWidget(self.tabs)

        main.addWidget(body, stretch=1)

        # Status bar
        self.status_bar = QLabel("  Ready")
        self.status_bar.setFixedHeight(20)
        self.status_bar.setStyleSheet(
            "color: #8b949e; font-size: 10px; padding-left: 8px;")
        main.addWidget(self.status_bar)

        # Mở tab đầu tiên
        self._new_tab(HOME_URL)

    # ── Tab management ──────────────────────────────

    def _new_tab(self, url=HOME_URL):
        tab = BrowserTab(url)
        tab.title_changed.connect(
            lambda t, tab=tab: self._set_tab_title(tab, t))
        tab.url_changed.connect(self._on_url_changed)
        tab.load_progress.connect(self._on_progress)

        idx = self.tabs.addTab(tab, "🌐  New Tab")
        self.tabs.setCurrentIndex(idx)
        self.addr_bar.setFocus()

        # Set bookmark get_url callback
        self.bm_panel._get_url = self._current_url
        return tab

    def _close_tab(self, idx):
        if self.tabs.count() == 1:
            self._new_tab()
        self.tabs.removeTab(idx)

    def _current_tab(self):
        return self.tabs.currentWidget()

    def _set_tab_title(self, tab, title):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            short = title[:20] + "…" if len(title) > 20 else title
            self.tabs.setTabText(idx, short or "New Tab")

    # ── Navigation ──────────────────────────────────

    def _go(self):
        text = self.addr_bar.text().strip()
        if not text:
            return
        # Nếu trông như URL thì load, không thì Google search
        if "." in text and " " not in text:
            url = text if text.startswith("http") else "https://" + text
        else:
            url = "https://www.google.com/search?q=" + text.replace(" ", "+")
        self._load_url(url)

    def _load_url(self, url):
        tab = self._current_tab()
        if tab:
            tab.load(url)

    def _back(self):
        t = self._current_tab()
        if t: t.back()

    def _forward(self):
        t = self._current_tab()
        if t: t.forward()

    def _reload(self):
        t = self._current_tab()
        if t: t.reload()

    def _home(self):
        self._load_url(HOME_URL)

    def _current_url(self):
        t = self._current_tab()
        return t.current_url() if t else ""

    # ── Events ──────────────────────────────────────

    def _on_tab_change(self, idx):
        tab = self.tabs.widget(idx)
        if tab:
            url = tab.current_url()
            if url:
                self.addr_bar.setText(url)

    def _on_url_changed(self, url):
        t = self._current_tab()
        if t and t.current_url() == url:
            self.addr_bar.setText(url)
            self.status_bar.setText(f"  {url}")

    def _on_progress(self, v):
        if v < 100:
            self.progress.show()
            self.progress.setValue(v)
            self.btn_reload.setText("✕")
        else:
            self.progress.hide()
            self.btn_reload.setText("↺")

    def _toggle_bookmarks(self):
        if self.bm_panel.isHidden():
            self.bm_panel.show()
        else:
            self.bm_panel.hide()
