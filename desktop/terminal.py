import os
import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor


class MixtralrTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('🖥  Terminal')
        self.setMinimumSize(600, 380)
        self.hist = []
        self.hidx = 0
        self.cwd = os.path.expanduser('~')  # each terminal tracks its own cwd

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Monospace", 11))
        self.out.setMaximumBlockCount(2000)

        prompt_row = QHBoxLayout()
        prompt_row.setContentsMargins(6, 4, 6, 6)
        self.prompt_lbl = QLabel("$ ")
        self.prompt_lbl.setFont(QFont("Monospace", 11))
        self.prompt_lbl.setObjectName("TermPrompt")

        self.cmd = QLineEdit()
        self.cmd.setFont(QFont("Monospace", 11))
        self.cmd.setPlaceholderText("Enter command...")
        self.cmd.returnPressed.connect(self.run)
        self.cmd.installEventFilter(self)

        prompt_row.addWidget(self.prompt_lbl)
        prompt_row.addWidget(self.cmd)

        layout.addWidget(self.out)
        layout.addLayout(prompt_row)

        self._print("Mixtralr Terminal  —  type 'help' for commands\n", "#89b4fa")

    def _print(self, text, color=None):
        cursor = self.out.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.out.setTextCursor(cursor)
        self.out.ensureCursorVisible()

    def eventFilter(self, obj, event):
        if obj is self.cmd and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                if self.hidx > 0:
                    self.hidx -= 1
                    self.cmd.setText(self.hist[self.hidx])
                return True
            elif key == Qt.Key.Key_Down:
                if self.hidx < len(self.hist) - 1:
                    self.hidx += 1
                    self.cmd.setText(self.hist[self.hidx])
                else:
                    self.hidx = len(self.hist)
                    self.cmd.clear()
                return True
            elif key == Qt.Key.Key_Tab:
                # Tab completion cơ bản
                import glob, os
                text = self.cmd.text()
                matches = glob.glob(text + '*')
                if len(matches) == 1:
                    self.cmd.setText(matches[0])
                elif len(matches) > 1:
                    self._print('\t'.join([os.path.basename(m) for m in matches]) + '\n')
                return True
        return super().eventFilter(obj, event)

    def run(self):
        c = self.cmd.text().strip()
        if not c:
            return
        self.hist.append(c)
        self.hidx = len(self.hist)
        self._print(f"$ {c}\n", "#a6e3a1")

        # Built-in cd
        if c.startswith('cd ') or c == 'cd':
            import os
            path = c[3:].strip() if c != 'cd' else os.path.expanduser('~')
            if not os.path.isabs(path):
                path = os.path.join(self.cwd or os.path.expanduser('~'), path)
            path = os.path.normpath(path)
            if os.path.isdir(path):
                self.cwd = path
                self._print(f"→ {path}\n", "#8b949e")
            else:
                self._print(f"cd: {path}: No such directory\n", "#f38ba8")
            self.cmd.clear()
            return

        if c == 'clear':
            self.out.clear()
            self.cmd.clear()
            return

        try:
            p = subprocess.run(
                c, shell=True, capture_output=True,
                text=True, executable='/bin/bash',
                cwd=self.cwd, timeout=30
            )
            if p.stdout:
                self._print(p.stdout)
            if p.stderr:
                self._print(p.stderr, "#f38ba8")
        except subprocess.TimeoutExpired:
            self._print("Command timed out (30s)\n", "#fab387")
        except Exception as e:
            self._print(str(e) + '\n', "#f38ba8")

        self.cmd.clear()
