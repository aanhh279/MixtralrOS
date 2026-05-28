#!/usr/bin/env python3
"""Task Manager – MixtralOS (real-time CPU/RAM, process list, kill)"""
import os, time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QTabWidget, QFrame, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class DataWorker(QThread):
    """Chạy psutil trong thread riêng để không block UI"""
    data_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._running = True
        self._last_net = None

    def run(self):
        while self._running:
            if _HAS_PSUTIL:
                try:
                    cpu     = psutil.cpu_percent(interval=0.5)
                    mem     = psutil.virtual_memory()
                    disk    = psutil.disk_usage("/")
                    net_now = psutil.net_io_counters()
                    if self._last_net:
                        sent = (net_now.bytes_sent - self._last_net.bytes_sent) // 1024
                        recv = (net_now.bytes_recv - self._last_net.bytes_recv) // 1024
                    else:
                        sent = recv = 0
                    self._last_net = net_now

                    procs = []
                    for p in psutil.process_iter(
                            ["pid","name","cpu_percent","memory_info","status","username"]):
                        try:
                            info = p.info
                            procs.append({
                                "pid":    info["pid"],
                                "name":   info["name"] or "",
                                "cpu":    info["cpu_percent"] or 0.0,
                                "mem":    (info["memory_info"].rss // 1024 // 1024
                                           if info["memory_info"] else 0),
                                "status": info["status"] or "",
                                "user":   info["username"] or "",
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    procs.sort(key=lambda x: x["cpu"], reverse=True)

                    self.data_ready.emit({
                        "cpu": cpu,
                        "mem_used":  mem.used   // 1024 // 1024,
                        "mem_total": mem.total  // 1024 // 1024,
                        "mem_pct":   mem.percent,
                        "disk_used":  disk.used  // 1024 // 1024 // 1024,
                        "disk_total": disk.total // 1024 // 1024 // 1024,
                        "disk_pct":   disk.percent,
                        "net_sent": sent,
                        "net_recv": recv,
                        "procs":    procs,
                    })
                except Exception:
                    pass
            else:
                self.data_ready.emit({"no_psutil": True})
                time.sleep(2)

    def stop(self):
        self._running = False


def _bar_style(pct):
    if pct < 60:   c = "#3fb950"
    elif pct < 80: c = "#d29922"
    else:          c = "#f85149"
    return (f"QProgressBar{{background:#21262d; border:none; border-radius:4px; height:14px;}}"
            f"QProgressBar::chunk{{background:{c}; border-radius:4px;}}")


class MixtralrTaskManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊  Task Manager")
        self.setMinimumSize(780, 540)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;}
            QTabBar::tab{background:#161b22;color:#8b949e;padding:8px 18px;border:1px solid #30363d;
                border-bottom:none;border-radius:4px 4px 0 0;}
            QTabBar::tab:selected{background:#21262d;color:#58a6ff;}
        """)
        root.addWidget(tabs)

        tabs.addTab(self._build_perf_tab(),    "📈 Performance")
        tabs.addTab(self._build_process_tab(), "⚙  Processes")

        # Worker thread
        self._worker = DataWorker()
        self._worker.data_ready.connect(self._update_data)
        self._worker.start()

    # ── Performance tab ──────────────────────────────────────────
    def _build_perf_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        def mkrow(label, bar_attr, lbl_attr):
            row = QHBoxLayout()
            lbl = QLabel(label); lbl.setFixedWidth(110)
            lbl.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
            bar = QProgressBar()
            bar.setRange(0, 100); bar.setTextVisible(False); bar.setFixedHeight(14)
            val = QLabel("—"); val.setFixedWidth(90)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setFont(QFont("DejaVu Sans", 10))
            row.addWidget(lbl); row.addWidget(bar); row.addWidget(val)
            setattr(self, bar_attr, bar)
            setattr(self, lbl_attr, val)
            return row

        lay.addLayout(mkrow("🖥  CPU",    "_cpu_bar",  "_cpu_lbl"))
        lay.addLayout(mkrow("🧠 Memory", "_mem_bar",  "_mem_lbl"))
        lay.addLayout(mkrow("💾 Disk",   "_disk_bar", "_disk_lbl"))

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#30363d;"); lay.addWidget(sep)

        # Network
        net_row = QHBoxLayout()
        net_lbl = QLabel("🌐 Network")
        net_lbl.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
        net_lbl.setFixedWidth(110)
        self._net_lbl = QLabel("↑ — KB/s   ↓ — KB/s")
        self._net_lbl.setStyleSheet("color:#58a6ff;")
        net_row.addWidget(net_lbl); net_row.addWidget(self._net_lbl)
        lay.addLayout(net_row)

        lay.addStretch()

        # Sys info grid
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:#30363d;"); lay.addWidget(sep2)
        self._sysinfo = QLabel("")
        self._sysinfo.setFont(QFont("Monospace", 9))
        self._sysinfo.setStyleSheet("color:#8b949e;")
        self._sysinfo.setWordWrap(True)
        lay.addWidget(self._sysinfo)
        self._load_sysinfo()

        return w

    def _load_sysinfo(self):
        if not _HAS_PSUTIL: return
        try:
            boot = time.strftime("%Y-%m-%d %H:%M", time.localtime(psutil.boot_time()))
            cpus = psutil.cpu_count(logical=True)
            phys = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "—"
            self._sysinfo.setText(
                f"Boot: {boot}   CPUs: {phys}p/{cpus}L @ {freq_str}"
            )
        except Exception:
            pass

    # ── Process tab ──────────────────────────────────────────────
    def _build_process_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Search + buttons
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Filter processes...")
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(self._filter_procs)
        self._search.setStyleSheet(
            "background:#21262d; border:1px solid #30363d; border-radius:4px;"
            "padding:2px 8px; color:#e6edf3;"
        )

        kill_btn = QPushButton("🛑 End Task")
        kill_btn.setFixedHeight(30)
        kill_btn.clicked.connect(self._kill_process)
        kill_btn.setStyleSheet(
            "background:#4a0f0f; color:#f85149; border:1px solid #6a1f1f; border-radius:4px; padding:2px 10px;"
        )

        self._proc_count = QLabel("0 processes")
        self._proc_count.setStyleSheet("color:#8b949e; font-size:10px;")

        top.addWidget(self._search)
        top.addWidget(kill_btn)
        top.addWidget(self._proc_count)
        lay.addLayout(top)

        # Table
        cols = ["PID", "Name", "CPU%", "RAM (MB)", "Status", "User"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 60)
        self._table.setColumnWidth(2, 65)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 90)
        self._table.setColumnWidth(5, 110)
        self._table.setSortingEnabled(True)
        self._table.setStyleSheet("""
            QTableWidget{background:#0d1117;border:none;color:#e6edf3;
                gridline-color:#21262d;font-size:11px;}
            QHeaderView::section{background:#161b22;color:#8b949e;border:none;
                padding:5px;border-right:1px solid #30363d;font-size:11px;font-weight:bold;}
            QTableWidget::item:selected{background:#1e3a5f;color:#58a6ff;}
        """)
        lay.addWidget(self._table)

        self._all_procs = []

        if not _HAS_PSUTIL:
            lay.addWidget(QLabel("⚠  psutil not installed – process list unavailable"))

        return w

    # ── Data update ──────────────────────────────────────────────
    def _update_data(self, d):
        if d.get("no_psutil"):
            return

        # Performance
        cpu  = d["cpu"]
        mf   = d["mem_used"]
        mt   = d["mem_total"]
        mp   = d["mem_pct"]
        df   = d["disk_used"]
        dt   = d["disk_total"]
        dp   = d["disk_pct"]

        self._cpu_bar.setValue(int(cpu))
        self._cpu_bar.setStyleSheet(_bar_style(cpu))
        self._cpu_lbl.setText(f"{cpu:.1f}%")

        self._mem_bar.setValue(int(mp))
        self._mem_bar.setStyleSheet(_bar_style(mp))
        self._mem_lbl.setText(f"{mf} / {mt} MB")

        self._disk_bar.setValue(int(dp))
        self._disk_bar.setStyleSheet(_bar_style(dp))
        self._disk_lbl.setText(f"{df} / {dt} GB")

        self._net_lbl.setText(f"↑ {d['net_sent']} KB/s   ↓ {d['net_recv']} KB/s")

        # Processes
        self._all_procs = d["procs"]
        flt = self._search.text().lower()
        self._populate_table([p for p in self._all_procs
                              if flt in p["name"].lower() or flt in str(p["pid"])])

    def _populate_table(self, procs):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            def cell(val, align=Qt.AlignmentFlag.AlignCenter):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                return it

            cpu_pct = p["cpu"]
            cpu_item = cell(f"{cpu_pct:.1f}")
            if cpu_pct > 50: cpu_item.setForeground(QColor("#f85149"))
            elif cpu_pct > 20: cpu_item.setForeground(QColor("#d29922"))
            else: cpu_item.setForeground(QColor("#3fb950"))

            mem_mb = p["mem"]
            mem_item = cell(str(mem_mb))
            if mem_mb > 500: mem_item.setForeground(QColor("#f85149"))

            self._table.setItem(r, 0, cell(str(p["pid"])))
            self._table.setItem(r, 1, cell(p["name"], Qt.AlignmentFlag.AlignLeft))
            self._table.setItem(r, 2, cpu_item)
            self._table.setItem(r, 3, mem_item)
            self._table.setItem(r, 4, cell(p["status"]))
            self._table.setItem(r, 5, cell(p["user"], Qt.AlignmentFlag.AlignLeft))
        self._table.setSortingEnabled(True)
        self._proc_count.setText(f"{len(procs)} processes")

    def _filter_procs(self, text):
        flt = text.lower()
        self._populate_table([p for p in self._all_procs
                              if flt in p["name"].lower() or flt in str(p["pid"])])

    def _kill_process(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a process first.")
            return
        pid_item = self._table.item(row, 0)
        name_item = self._table.item(row, 1)
        if not pid_item: return
        pid  = int(pid_item.text())
        name = name_item.text() if name_item else str(pid)
        r = QMessageBox.question(self, "End Task",
            f"Terminate process '{name}' (PID {pid})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes: return
        try:
            import psutil
            p = psutil.Process(pid)
            p.terminate()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def closeEvent(self, e):
        self._worker.stop()
        self._worker.wait(1000)
        super().closeEvent(e)
