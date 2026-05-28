#!/usr/bin/env python3
"""Calculator – MixtralOS (full scientific mode + history + keyboard)"""
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QSplitter, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeyEvent


class CalcButton(QPushButton):
    def __init__(self, text, style="normal", span=1):
        super().__init__(text)
        self._style = style
        self.setFixedHeight(46)
        self.setFont(QFont("DejaVu Sans", 13))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_style()

    def _apply_style(self):
        styles = {
            "normal":   "background:#21262d; color:#e6edf3; border:1px solid #30363d; border-radius:8px;",
            "op":       "background:#1e3a5f; color:#58a6ff; border:1px solid #2d4a6f; border-radius:8px;",
            "equals":   "background:#1a4a9f; color:#ffffff; border:1px solid #2060cf; border-radius:8px; font-weight:bold;",
            "clear":    "background:#4a0f0f; color:#ff6b6b; border:1px solid #6a1f1f; border-radius:8px; font-weight:bold;",
            "func":     "background:#1a2a1a; color:#3fb950; border:1px solid #2a4a2a; border-radius:8px;",
            "mem":      "background:#2a1a3a; color:#bc8cff; border:1px solid #3a2a5a; border-radius:8px;",
        }
        base = styles.get(self._style, styles["normal"])
        self.setStyleSheet(f"""
            QPushButton {{ {base} padding:4px; }}
            QPushButton:hover {{ brightness: 130%; filter: brightness(1.3); border-color: #58a6ff; }}
            QPushButton:pressed {{ background: #58a6ff; color: #0d1117; }}
        """)


class MixtralrCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧮  Calculator")
        self.setMinimumSize(340, 520)
        self._expr       = ""
        self._just_equal = False
        self._mem        = 0.0
        self._history    = []
        self._sci_mode   = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # ── Display ──────────────────────────────────────────────
        disp_frame = QWidget()
        disp_frame.setStyleSheet("background:#0d1117; border-radius:10px; padding:4px;")
        disp_lay = QVBoxLayout(disp_frame)
        disp_lay.setContentsMargins(12, 8, 12, 8)
        disp_lay.setSpacing(2)

        self._expr_lbl = QLabel("")
        self._expr_lbl.setFont(QFont("DejaVu Sans", 9))
        self._expr_lbl.setStyleSheet("color:#555; background:transparent;")
        self._expr_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        disp_lay.addWidget(self._expr_lbl)

        self._display = QLineEdit("0")
        self._display.setReadOnly(True)
        self._display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._display.setFont(QFont("DejaVu Sans", 28, QFont.Weight.Bold))
        self._display.setStyleSheet(
            "background:transparent; border:none; color:#e6edf3; selection-background-color:#58a6ff;"
        )
        self._display.setFixedHeight(60)
        disp_lay.addWidget(self._display)

        self._mem_lbl = QLabel("")
        self._mem_lbl.setFont(QFont("DejaVu Sans", 8))
        self._mem_lbl.setStyleSheet("color:#bc8cff; background:transparent;")
        disp_lay.addWidget(self._mem_lbl)

        root.addWidget(disp_frame)

        # ── Mode toggle ─────────────────────────────────────────
        mode_row = QHBoxLayout()
        self._mode_btn = QPushButton("📐 Scientific")
        self._mode_btn.setFixedHeight(28)
        self._mode_btn.setFont(QFont("DejaVu Sans", 9))
        self._mode_btn.clicked.connect(self._toggle_mode)
        self._mode_btn.setStyleSheet(
            "background:#21262d; color:#58a6ff; border:1px solid #30363d; border-radius:6px; padding:2px 10px;"
        )
        mode_row.addStretch()
        mode_row.addWidget(self._mode_btn)
        root.addLayout(mode_row)

        # ── Splitter: buttons | history ─────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self._splitter, stretch=1)

        # Buttons panel
        btn_widget = QWidget()
        self._btn_grid = QGridLayout(btn_widget)
        self._btn_grid.setSpacing(6)
        self._btn_grid.setContentsMargins(0, 0, 0, 0)
        self._splitter.addWidget(btn_widget)

        # History panel
        hist_widget = QWidget()
        hist_widget.setMinimumWidth(130)
        hist_lay = QVBoxLayout(hist_widget)
        hist_lay.setContentsMargins(4, 0, 0, 0)
        hist_lay.setSpacing(4)
        hist_hdr = QLabel("📋 History")
        hist_hdr.setFont(QFont("DejaVu Sans", 9, QFont.Weight.Bold))
        hist_hdr.setStyleSheet("color:#8b949e;")
        self._hist_list = QListWidget()
        self._hist_list.setStyleSheet(
            "background:#0d1117; border:1px solid #30363d; border-radius:6px;"
            "color:#e6edf3; font-size:10px;"
        )
        self._hist_list.itemClicked.connect(self._use_history)
        clr_hist = QPushButton("🗑 Clear")
        clr_hist.setFixedHeight(24)
        clr_hist.setFont(QFont("DejaVu Sans", 8))
        clr_hist.clicked.connect(self._clear_history)
        clr_hist.setStyleSheet(
            "background:#21262d; color:#e6edf3; border:1px solid #30363d; border-radius:4px;"
        )
        hist_lay.addWidget(hist_hdr)
        hist_lay.addWidget(self._hist_list, stretch=1)
        hist_lay.addWidget(clr_hist)
        self._splitter.addWidget(hist_widget)
        self._splitter.setSizes([220, 130])

        self._build_buttons()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Button layout ────────────────────────────────────────────
    def _clear_grid(self):
        while self._btn_grid.count():
            item = self._btn_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_buttons(self):
        self._clear_grid()
        g = self._btn_grid

        if self._sci_mode:
            sci_buttons = [
                # row 0: memory
                [("MC","mem"),("MR","mem"),("M+","mem"),("M-","mem"),("MS","mem")],
                # row 1: sci functions
                [("sin","func"),("cos","func"),("tan","func"),("log","func"),("ln","func")],
                # row 2: more sci
                [("x²","func"),("√","func"),("xʸ","func"),("π","func"),("e","func")],
                # row 3
                [("C","clear"),("±","op"),("%","op"),("⌫","op"),("÷","op")],
                # row 4-7: digits + ops
                [("7","normal"),("8","normal"),("9","normal"),("×","op")],
                [("4","normal"),("5","normal"),("6","normal"),("−","op")],
                [("1","normal"),("2","normal"),("3","normal"),("＋","op")],
                [("(","func"),("0","normal"),(".",  "normal"),("=","equals")],
            ]
            spans = {(3,3):1,(3,4):1,(4,3):1,(5,3):1,(6,3):1,(7,3):1}
        else:
            sci_buttons = [
                [("MC","mem"),("MR","mem"),("M+","mem"),("M-","mem")],
                [("C","clear"),("±","op"),("%","op"),("⌫","op")],
                [("7","normal"),("8","normal"),("9","normal"),("÷","op")],
                [("4","normal"),("5","normal"),("6","normal"),("×","op")],
                [("1","normal"),("2","normal"),("3","normal"),("−","op")],
                [("0","normal",2),(".", "normal"),("=","equals"),("＋","op")],
            ]
            spans = {}

        for row_i, row in enumerate(sci_buttons):
            col_i = 0
            for item in row:
                text  = item[0]
                style = item[1] if len(item) > 1 else "normal"
                span  = item[2] if len(item) > 2 else 1
                btn   = CalcButton(text, style, span)
                btn.clicked.connect(lambda _, t=text: self._on_btn(t))
                g.addWidget(btn, row_i, col_i, 1, span)
                col_i += span

    def _toggle_mode(self):
        self._sci_mode = not self._sci_mode
        self._mode_btn.setText("🔢 Standard" if self._sci_mode else "📐 Scientific")
        self._build_buttons()

    # ── Button handler ───────────────────────────────────────────
    def _on_btn(self, t):
        cur = self._display.text()
        err = cur in ("Error", "∞", "-∞", "nan")

        # Clear
        if t == "C":
            self._expr = ""
            self._display.setText("0")
            self._expr_lbl.setText("")
            self._just_equal = False
            return

        if t == "⌫":
            if err or self._just_equal:
                self._display.setText("0")
                self._expr = ""
                self._just_equal = False
            else:
                new = cur[:-1] or "0"
                self._display.setText(new)
            return

        if t == "=":
            self._calculate()
            return

        # Memory
        if t == "MC":  self._mem = 0.0;  self._mem_lbl.setText(""); return
        if t == "MR":
            self._input_value(str(self._mem)); return
        if t in ("M+", "M-"):
            try:
                v = float(self._display.text())
                self._mem = self._mem + v if t == "M+" else self._mem - v
                self._mem_lbl.setText(f"M = {self._mem:g}")
            except ValueError: pass
            return
        if t == "MS":
            try:
                self._mem = float(self._display.text())
                self._mem_lbl.setText(f"M = {self._mem:g}")
            except ValueError: pass
            return

        # Unary functions
        unary = {
            "sin": lambda x: math.sin(math.radians(x)),
            "cos": lambda x: math.cos(math.radians(x)),
            "tan": lambda x: math.tan(math.radians(x)),
            "log": math.log10,
            "ln":  math.log,
            "x²":  lambda x: x**2,
            "√":   math.sqrt,
            "π":   None,  # constant
            "e":   None,  # constant
            "±":   lambda x: -x,
        }
        if t in unary:
            if t == "π":   self._input_value(str(math.pi)); return
            if t == "e":   self._input_value(str(math.e));  return
            try:
                v = float(cur)
                r = unary[t](v)
                self._add_history(f"{t}({cur})", r)
                self._display.setText(self._fmt(r))
                self._just_equal = True
            except Exception:
                self._display.setText("Error")
            return

        # Constants
        if t == "%":
            try:
                self._display.setText(self._fmt(float(cur) / 100))
                self._just_equal = True
            except ValueError: pass
            return

        # xʸ → start power expression
        if t == "xʸ":
            self._expr = cur + "**"
            self._display.setText("0")
            self._expr_lbl.setText(f"{cur} ^")
            self._just_equal = False
            return

        # Operators
        op_map = {"÷": "/", "×": "*", "−": "-", "＋": "+", "(": "(", ")": ")"}
        if t in op_map:
            if self._just_equal:
                self._expr = cur + op_map[t]
            else:
                self._expr += (cur if not self._just_equal else "") + op_map[t]
            cur_expr = self._expr.replace("/","÷").replace("*","×").replace("-","−").replace("+","＋")
            self._expr_lbl.setText(cur_expr[:40])
            self._display.setText("0")
            self._just_equal = False
            return

        # Digits / decimal
        if self._just_equal or err:
            self._expr = ""
            cur = "0"
            self._just_equal = False

        if t == ".":
            if "." not in cur:
                self._display.setText(cur + ".")
        else:
            if cur == "0":
                self._display.setText(t)
            else:
                self._display.setText(cur + t)

    def _input_value(self, val):
        self._display.setText(val)
        self._just_equal = True

    def _calculate(self):
        cur = self._display.text()
        if cur in ("Error",):
            return
        try:
            full_expr = self._expr + cur
            result = eval(full_expr, {"__builtins__": {}})
            result_str = self._fmt(result)
            display_expr = (self._expr + cur).replace("/","÷").replace("*","×").replace("-","−").replace("+","＋")
            self._add_history(display_expr, result)
            self._expr_lbl.setText(display_expr + " =")
            self._display.setText(result_str)
            self._expr = ""
            self._just_equal = True
        except ZeroDivisionError:
            self._display.setText("∞")
            self._just_equal = True
        except Exception:
            self._display.setText("Error")
            self._just_equal = True

    @staticmethod
    def _fmt(n):
        if isinstance(n, (int, float)):
            if n == int(n) and abs(n) < 1e15:
                return str(int(n))
            return f"{n:.10g}"
        return str(n)

    def _add_history(self, expr, result):
        entry = f"{expr} = {self._fmt(result)}"
        self._history.insert(0, entry)
        self._history = self._history[:50]
        item = QListWidgetItem(entry)
        self._hist_list.insertItem(0, item)
        if self._hist_list.count() > 50:
            self._hist_list.takeItem(50)

    def _use_history(self, item):
        try:
            val = item.text().split("=")[-1].strip()
            self._display.setText(val)
            self._just_equal = True
        except Exception: pass

    def _clear_history(self):
        self._history.clear()
        self._hist_list.clear()

    # ── Keyboard support ─────────────────────────────────────────
    def keyPressEvent(self, e: QKeyEvent):
        key = e.key()
        text = e.text()
        map_ = {
            Qt.Key.Key_Return:    "=",
            Qt.Key.Key_Enter:     "=",
            Qt.Key.Key_Backspace: "⌫",
            Qt.Key.Key_Escape:    "C",
            Qt.Key.Key_Plus:      "＋",
            Qt.Key.Key_Minus:     "−",
            Qt.Key.Key_Asterisk:  "×",
            Qt.Key.Key_Slash:     "÷",
            Qt.Key.Key_Percent:   "%",
        }
        if key in map_:
            self._on_btn(map_[key])
        elif text.isdigit() or text == ".":
            self._on_btn(text)
        else:
            super().keyPressEvent(e)
