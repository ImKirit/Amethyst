"""Title bar with the three Windows buttons, drawn by hand.

The glyphs are the ones Windows itself uses (Segoe MDL2 Assets), so minimize,
maximize and close look like they do in any other window. The behaviour is
native as well: dragging, snapping and the double click come from Windows,
see ``winapi/window_frame.py``.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from . import theme
from .widgets import Badge

# Segoe MDL2 Assets, the glyph set the Windows title bars use
GLYPH_MINIMIZE = ""
GLYPH_MAXIMIZE = ""
GLYPH_RESTORE = ""
GLYPH_CLOSE = ""


class WindowButton(QPushButton):
    """One of the three buttons on the right, in Windows proportions."""

    def __init__(self, glyph: str, tooltip: str, close: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._glyph = glyph
        self._close = close
        self.setFixedSize(46, 32)
        self.setToolTip(tooltip)
        self.setCursor(Qt.ArrowCursor)
        self.setFlat(True)
        self.setStyleSheet("border: none; background: transparent;")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())

        if self.underMouse():
            painter.fillRect(rect, QColor(theme.DANGER) if self._close
                             else QColor(255, 255, 255, 26))

        font = QFont("Segoe MDL2 Assets", 8)
        painter.setFont(font)
        painter.setPen(QColor("#1A0A0A") if (self._close and self.underMouse())
                       else QColor(theme.TEXT))
        painter.drawText(rect, Qt.AlignCenter, self._glyph)
        painter.end()

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.update()


class TitleBar(QWidget):
    """App name on the left, status in the middle, window buttons on the right."""

    minimizeRequested = Signal()
    maximizeRequested = Signal()
    closeRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(10)

        self.status_badge = Badge("No game detected", theme.TEXT_MUTED)
        layout.addWidget(self.status_badge, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        self.message = QLabel("")
        self.message.setObjectName("faint")
        layout.addWidget(self.message, 0, Qt.AlignVCenter)
        layout.addSpacing(8)

        self.minimize_button = WindowButton(GLYPH_MINIMIZE, "Minimize")
        self.maximize_button = WindowButton(GLYPH_MAXIMIZE, "Maximize")
        self.close_button = WindowButton(GLYPH_CLOSE, "Close", close=True)
        self.minimize_button.clicked.connect(self.minimizeRequested.emit)
        self.maximize_button.clicked.connect(self.maximizeRequested.emit)
        self.close_button.clicked.connect(self.closeRequested.emit)
        for button in (self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button, 0, Qt.AlignTop)

    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.set_glyph(GLYPH_RESTORE if maximized else GLYPH_MAXIMIZE)
        self.maximize_button.setToolTip("Restore" if maximized else "Maximize")

    def is_on_buttons(self, x: int, y: int) -> bool:
        """True when the point sits on one of the three buttons."""
        child = self.childAt(x, y)
        return isinstance(child, WindowButton)
