from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont


class NotificationCenter(QWidget):
    def __init__(self, desktop):
        super().__init__(desktop)
        self.desktop = desktop
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(6)
        self.setFixedWidth(320)
        self._reposition()
        self.hide()

    def _reposition(self):
        screen = self.desktop.screen().geometry()
        self.move(screen.width() - 330, 10)

    def push(self, title, text):
        card = QWidget()
        card.setFixedWidth(310)
        card.setObjectName("NotifCard")

        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 8, 12, 8)
        cl.setSpacing(2)

        top = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("DejaVu Sans", 10, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setFlat(True)
        top.addWidget(title_lbl)
        top.addStretch()
        top.addWidget(close_btn)

        body_lbl = QLabel(text)
        body_lbl.setWordWrap(True)
        body_lbl.setFont(QFont("DejaVu Sans", 9))

        cl.addLayout(top)
        cl.addWidget(body_lbl)

        t = self.desktop.theme
        card.setStyleSheet(f"""
            QWidget#NotifCard {{
                background: {t['surface']};
                border: 1px solid {t['accent']};
                border-radius: 8px;
            }}
            QLabel {{ color: {t['text']}; background: transparent; }}
            QPushButton {{
                color: {t['text']};
                border: none;
                background: transparent;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {t['accent']}; }}
        """)

        self.vbox.addWidget(card)
        self.show()
        self.raise_()
        self.adjustSize()

        def remove(c=card):
            self.vbox.removeWidget(c)
            c.deleteLater()
            self.adjustSize()
            if self.vbox.count() == 0:
                self.hide()

        close_btn.clicked.connect(remove)
        QTimer.singleShot(5000, remove)
