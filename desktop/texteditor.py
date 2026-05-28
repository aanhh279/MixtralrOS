#!/usr/bin/env python3
"""Text Editor – MixtralOS (line numbers, find/replace, syntax highlight, tabs)"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QLineEdit, QCheckBox, QTabWidget, QFrame, QToolBar,
    QSizePolicy, QStatusBar
)
from PyQt6.QtCore import Qt, QRect, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QTextCharFormat, QSyntaxHighlighter,
    QTextDocument, QPalette, QKeySequence, QTextCursor
)


# ── Line number area ─────────────────────────────────────────────
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, e):
        self._editor._paint_line_numbers(e)


# ── Code editor with line numbers ────────────────────────────────
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self._lna = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_width()
        self.setTabStopDistance(28)
        self.setFont(QFont("Monospace", 11))

    def _line_number_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 6 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_width(self):
        self.setViewportMargins(self._line_number_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._lna.scroll(0, dy)
        else:
            self._lna.update(0, rect.y(), self._lna.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_width()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self._lna.setGeometry(QRect(cr.left(), cr.top(), self._line_number_width(), cr.height()))

    def _paint_line_numbers(self, e):
        p = QPainter(self._lna)
        p.fillRect(e.rect(), QColor("#161b22"))
        block  = self.firstVisibleBlock()
        num    = block.blockNumber()
        top    = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= e.rect().bottom():
            if block.isVisible() and bottom >= e.rect().top():
                p.setPen(QColor("#484f58"))
                p.setFont(self.font())
                p.drawText(0, top, self._lna.width() - 3,
                            self.fontMetrics().height(),
                            Qt.AlignmentFlag.AlignRight,
                            str(num + 1))
            block  = block.next()
            top    = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            num   += 1


# ── Syntax highlighter (Python + generic) ────────────────────────
class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, doc, ext=""):
        super().__init__(doc)
        self._rules = []
        self._ext   = ext
        self._setup(ext)

    def _fmt(self, color, bold=False, italic=False):
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:   f.setFontWeight(QFont.Weight.Bold)
        if italic: f.setFontItalic(True)
        return f

    def _setup(self, ext):
        import re
        kw  = self._fmt("#ff7b72", bold=True)
        str_= self._fmt("#a5d6ff")
        cmt = self._fmt("#8b949e", italic=True)
        num = self._fmt("#79c0ff")
        fn  = self._fmt("#d2a8ff")
        dec = self._fmt("#ffa657")

        if ext in (".py", ".pyw"):
            words = ["def","class","import","from","return","if","elif","else",
                     "for","while","in","not","and","or","True","False","None",
                     "try","except","finally","raise","with","as","pass","break",
                     "continue","lambda","yield","global","nonlocal","del","assert"]
            for w in words:
                self._rules.append((re.compile(r'\b' + w + r'\b'), kw))
            self._rules.append((re.compile(r'def\s+(\w+)'), fn))
            self._rules.append((re.compile(r'#[^\n]*'),      cmt))
            self._rules.append((re.compile(r'""".*?"""', re.DOTALL), cmt))
            self._rules.append((re.compile(r"'''.*?'''", re.DOTALL), cmt))
            self._rules.append((re.compile(r'(".*?"|\'.*?\')'),      str_))
            self._rules.append((re.compile(r'\b\d+\.?\d*\b'),        num))
            self._rules.append((re.compile(r'@\w+'),                 dec))
        elif ext in (".sh", ".bash"):
            self._rules.append((re.compile(r'#[^\n]*'),              cmt))
            words = ["if","then","fi","else","elif","for","in","do","done",
                     "while","case","esac","function","return","export","echo"]
            for w in words:
                self._rules.append((re.compile(r'\b' + w + r'\b'),   kw))
            self._rules.append((re.compile(r'"[^"]*"'),              str_))
            self._rules.append((re.compile(r"'[^']*'"),              str_))
            self._rules.append((re.compile(r'\$\w+|\$\{[^}]+\}'),   num))
        else:
            # Generic: strings, numbers
            self._rules.append((re.compile(r'"[^"]*"'),              str_))
            self._rules.append((re.compile(r"'[^']*'"),              str_))
            self._rules.append((re.compile(r'\b\d+\.?\d*\b'),        num))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ── Find/Replace bar ─────────────────────────────────────────────
class FindBar(QWidget):
    def __init__(self, editor_ref):
        super().__init__()
        self._ed = editor_ref
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        self.find_edit = QLineEdit(); self.find_edit.setPlaceholderText("🔍 Find...")
        self.find_edit.setFixedHeight(28); self.find_edit.returnPressed.connect(self._find_next)
        self.replace_edit = QLineEdit(); self.replace_edit.setPlaceholderText("Replace with...")
        self.replace_edit.setFixedHeight(28)
        self.case_cb = QCheckBox("Aa"); self.case_cb.setToolTip("Case sensitive")
        self.regex_cb = QCheckBox(".*"); self.regex_cb.setToolTip("Regex")

        btn_next    = QPushButton("▼ Next");     btn_next.setFixedHeight(28)
        btn_prev    = QPushButton("▲ Prev");     btn_prev.setFixedHeight(28)
        btn_replace = QPushButton("Replace");    btn_replace.setFixedHeight(28)
        btn_all     = QPushButton("Replace All"); btn_all.setFixedHeight(28)
        btn_close   = QPushButton("✕");           btn_close.setFixedSize(28, 28)

        btn_next.clicked.connect(self._find_next)
        btn_prev.clicked.connect(self._find_prev)
        btn_replace.clicked.connect(self._replace_once)
        btn_all.clicked.connect(self._replace_all)
        btn_close.clicked.connect(self.hide)

        self._count_lbl = QLabel(""); self._count_lbl.setFixedWidth(60)
        self._count_lbl.setStyleSheet("color:#8b949e; font-size:9px;")

        for w in [QLabel("Find:"), self.find_edit, self.case_cb, self.regex_cb,
                  btn_prev, btn_next, self._count_lbl,
                  QLabel("→"), self.replace_edit, btn_replace, btn_all, btn_close]:
            lay.addWidget(w)

        self.setStyleSheet(
            "QWidget{background:#161b22; border-top:1px solid #30363d;}"
            "QLineEdit{background:#0d1117; border:1px solid #30363d; border-radius:4px;"
            "padding:2px 6px; color:#e6edf3;}"
            "QPushButton{background:#21262d; color:#e6edf3; border:1px solid #30363d;"
            "border-radius:4px; padding:2px 8px;}"
            "QPushButton:hover{border-color:#58a6ff; color:#58a6ff;}"
            "QCheckBox{color:#8b949e;}"
        )
        self.hide()

    def _get_flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _find_next(self):
        self._find(False)

    def _find_prev(self):
        self._find(True)

    def _find(self, backward):
        ed = self._ed()
        if not ed: return
        text = self.find_edit.text()
        if not text: return
        flags = self._get_flags()
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        found = ed.find(text, flags)
        if not found:
            # Wrap around
            cur = ed.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start if not backward
                             else QTextCursor.MoveOperation.End)
            ed.setTextCursor(cur)
            ed.find(text, flags)
        self._update_count()

    def _update_count(self):
        ed = self._ed()
        if not ed: return
        text = self.find_edit.text()
        if not text: self._count_lbl.setText(""); return
        n = ed.document().toPlainText().count(text)
        self._count_lbl.setText(f"{n} found")

    def _replace_once(self):
        ed = self._ed()
        if not ed: return
        cur = ed.textCursor()
        if cur.hasSelection():
            cur.insertText(self.replace_edit.text())
        self._find_next()

    def _replace_all(self):
        ed = self._ed()
        if not ed: return
        text = self.find_edit.text()
        repl = self.replace_edit.text()
        if not text: return
        content = ed.toPlainText()
        flags = Qt.CaseSensitivity.CaseSensitive if self.case_cb.isChecked() else Qt.CaseSensitivity.CaseInsensitive
        import re
        pattern = re.escape(text) if not self.regex_cb.isChecked() else text
        cflags  = 0 if self.case_cb.isChecked() else re.IGNORECASE
        new_content, n = re.subn(pattern, repl, content, flags=cflags)
        if n:
            ed.setPlainText(new_content)
        self._count_lbl.setText(f"{n} replaced")


# ── Single tab editor ────────────────────────────────────────────
class EditorTab(QWidget):
    modified_changed = pyqtSignal(bool)

    def __init__(self, path=""):
        super().__init__()
        self.path     = path
        self._modified = False
        self._highlighter = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.editor = CodeEditor()
        self.editor.document().contentsChanged.connect(self._on_change)
        lay.addWidget(self.editor)

        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    self.editor.setPlainText(f.read())
                self._apply_highlight()
            except OSError: pass
        self._modified = False

    def _apply_highlight(self):
        ext = os.path.splitext(self.path)[1].lower() if self.path else ""
        if self._highlighter:
            self._highlighter.setDocument(None)
        self._highlighter = SyntaxHighlighter(self.editor.document(), ext)

    def _on_change(self):
        if not self._modified:
            self._modified = True
            self.modified_changed.emit(True)

    def display_name(self):
        base = os.path.basename(self.path) if self.path else "Untitled"
        return ("• " if self._modified else "") + base

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self._modified = False
            self.modified_changed.emit(False)
            return True
        except OSError as e:
            QMessageBox.critical(self, "Error", str(e))
            return False

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As",
            self.path or os.path.expanduser("~/untitled.txt"),
            "All Files (*)")
        if path:
            self.path = path
            self._apply_highlight()
            return self.save()
        return False


# ── Main text editor window ──────────────────────────────────────
class MixtralrTextEditor(QWidget):
    def __init__(self, path=""):
        super().__init__()
        self.setWindowTitle("📝  Text Editor")
        self.setMinimumSize(700, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        tb.setStyleSheet(
            "QToolBar{background:#161b22; border-bottom:1px solid #30363d; padding:2px 6px; spacing:4px;}"
            "QPushButton{background:#21262d; color:#e6edf3; border:1px solid #30363d;"
            "border-radius:4px; padding:3px 10px; font-size:11px;}"
            "QPushButton:hover{border-color:#58a6ff; color:#58a6ff;}"
        )
        tb_lay = QHBoxLayout()
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)

        def mkbtn(label, tip, slot):
            b = QPushButton(label); b.setToolTip(tip)
            b.setFixedHeight(28); b.clicked.connect(slot)
            return b

        tb_lay.addWidget(mkbtn("📄 New",       "New file",       self._new_tab))
        tb_lay.addWidget(mkbtn("📂 Open",      "Open file",      self._open))
        tb_lay.addWidget(mkbtn("💾 Save",      "Save (Ctrl+S)",  self._save))
        tb_lay.addWidget(mkbtn("💾 Save As",   "Save as",        self._save_as))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setFixedWidth(1)
        sep.setStyleSheet("background:#30363d;"); tb_lay.addWidget(sep)
        tb_lay.addWidget(mkbtn("🔍 Find",      "Find/Replace",   self._toggle_find))
        tb_lay.addWidget(mkbtn("↩ Undo",       "Undo",           self._undo))
        tb_lay.addWidget(mkbtn("↪ Redo",       "Redo",           self._redo))
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine); sep2.setFixedWidth(1)
        sep2.setStyleSheet("background:#30363d;"); tb_lay.addWidget(sep2)
        tb_lay.addWidget(mkbtn("A+", "Font larger",  lambda: self._change_font(1)))
        tb_lay.addWidget(mkbtn("A-", "Font smaller", lambda: self._change_font(-1)))
        tb_lay.addStretch()
        self._word_count = QLabel("0 words")
        self._word_count.setStyleSheet("color:#8b949e; font-size:10px;")
        tb_lay.addWidget(self._word_count)

        tb_w = QWidget(); tb_w.setLayout(tb_lay)
        root.addWidget(tb_w)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.setStyleSheet("""
            QTabWidget::pane{border:none;}
            QTabBar::tab{background:#161b22;color:#8b949e;padding:6px 14px;border:1px solid #30363d;
                border-bottom:none;border-radius:4px 4px 0 0;font-size:11px;}
            QTabBar::tab:selected{background:#21262d;color:#e6edf3;}
            QTabBar::close-button{subcontrol-position:right;}
        """)
        root.addWidget(self._tabs, stretch=1)

        # Find bar
        self._find_bar = FindBar(self._current_editor)
        root.addWidget(self._find_bar)

        # Status bar
        self._status = QLabel("Ready")
        self._status.setStyleSheet(
            "background:#0d1117; color:#8b949e; padding:2px 10px; font-size:10px;"
            "border-top:1px solid #30363d;"
        )
        self._status.setFixedHeight(20)
        root.addWidget(self._status)

        # Word count timer
        self._wc_timer = QTimer(self)
        self._wc_timer.timeout.connect(self._update_word_count)
        self._wc_timer.start(1000)

        # Open initial file or blank tab
        if path and os.path.isfile(path):
            self._open_path(path)
        else:
            self._new_tab()

    def _current_editor_tab(self):
        w = self._tabs.currentWidget()
        return w if isinstance(w, EditorTab) else None

    def _current_editor(self):
        t = self._current_editor_tab()
        return t.editor if t else None

    def _new_tab(self, path=""):
        tab = EditorTab(path)
        tab.modified_changed.connect(lambda _: self._refresh_tab_title(tab))
        idx = self._tabs.addTab(tab, tab.display_name())
        self._tabs.setCurrentIndex(idx)
        tab.editor.setFocus()
        return tab

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open File", os.path.expanduser("~"),
            "All Files (*);; Python (*.py);; Text (*.txt *.md);; Shell (*.sh)")
        if path:
            self._open_path(path)

    def _open_path(self, path):
        # Check if already open
        for i in range(self._tabs.count()):
            t = self._tabs.widget(i)
            if isinstance(t, EditorTab) and t.path == path:
                self._tabs.setCurrentIndex(i)
                return
        self._new_tab(path)

    def _save(self):
        t = self._current_editor_tab()
        if t:
            ok = t.save()
            if ok:
                self._status.setText(f"Saved: {t.path}")
                self._refresh_tab_title(t)

    def _save_as(self):
        t = self._current_editor_tab()
        if t:
            ok = t.save_as()
            if ok:
                self._status.setText(f"Saved: {t.path}")
                self._refresh_tab_title(t)

    def _refresh_tab_title(self, tab):
        for i in range(self._tabs.count()):
            if self._tabs.widget(i) is tab:
                self._tabs.setTabText(i, tab.display_name())
                break

    def _close_tab(self, idx):
        t = self._tabs.widget(idx)
        if isinstance(t, EditorTab) and t._modified:
            r = QMessageBox.question(self, "Unsaved Changes",
                f"Save '{t.display_name()}' before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                if not t.save(): return
            elif r == QMessageBox.StandardButton.Cancel:
                return
        self._tabs.removeTab(idx)
        if self._tabs.count() == 0:
            self._new_tab()

    def _on_tab_changed(self, _):
        self._update_word_count()

    def _toggle_find(self):
        if self._find_bar.isHidden():
            self._find_bar.show()
            self._find_bar.find_edit.setFocus()
        else:
            self._find_bar.hide()

    def _undo(self):
        e = self._current_editor()
        if e: e.undo()

    def _redo(self):
        e = self._current_editor()
        if e: e.redo()

    def _change_font(self, delta):
        e = self._current_editor()
        if not e: return
        f = e.font()
        f.setPointSize(max(6, f.pointSize() + delta))
        e.setFont(f)

    def _update_word_count(self):
        e = self._current_editor()
        if not e: return
        text  = e.toPlainText()
        words = len(text.split())
        chars = len(text)
        lines = text.count("\n") + 1
        self._word_count.setText(f"{words}w  {chars}c  {lines}L")
