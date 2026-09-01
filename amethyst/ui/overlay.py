"""Small always on top badge that shows which resolution is currently applied.

It is a separate top level window, not part of the main window, so it stays
visible while a game is in the foreground. One limitation is worth knowing:
a game running in exclusive full screen paints over everything, so the badge
shows up on the desktop and in borderless windowed mode, but not inside an
exclusive full screen game.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from . import theme

MARGIN = 24


class ResolutionOverlay(QWidget):
    """Draggable badge: 'Resolution: Stretched (1440 x 1080)'."""

    def __init__(self, store) -> None:
        super().__init__(None)
        self.store = store
        self._press: QPoint | None = None
        self._label = ""
        self._stretched = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Drag to move. Turn this off in the Amethyst settings.")
        self.resize(250, 40)

    # -- content ------------------------------------------------------
    def show_mode(self, width: int, height: int, stretched: bool) -> None:
        self._label = f"{width} x {height}"
        self._stretched = stretched
        self._fit()
        self.restore_position()
        self.show()
        self.raise_()

    def _fit(self) -> None:
        font = QFont(theme.FONT, 10)
        font.setWeight(QFont.DemiBold)
        self.setFont(font)
        # 27 px for the dot on the left, 16 px of air on the right
        width = self.fontMetrics().horizontalAdvance(self._text()) + 30 + 20
        self.resize(width, 40)

    def _text(self) -> str:
        kind = "Stretched" if self._stretched else "Native"
        return f"Resolution: {kind} ({self._label})"

    # -- position -----------------------------------------------------
    def restore_position(self) -> None:
        settings = self.store.settings
        if settings.overlay_x >= 0 and settings.overlay_y >= 0:
            self.move(settings.overlay_x, settings.overlay_y)
            return
        self.reset_position()

    def reset_position(self) -> None:
        screen = self.screen() or self.window().screen()
        area = screen.availableGeometry() if screen else None
        if area is not None:
            self.move(area.left() + MARGIN, area.top() + MARGIN)

    def _store_position(self) -> None:
        settings = self.store.settings
        settings.overlay_x = self.x()
        settings.overlay_y = self.y()
        self.store.save_settings()

    # -- interaction --------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            self._press = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._press is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._press is not None:
            self._press = None
            self._store_position()

    # -- painting -----------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QBrush(QColor(14, 8, 24, 224)))
        painter.setPen(QPen(QColor(theme.ACCENT if self._stretched else theme.BORDER), 1.4))
        painter.drawPath(path)

        dot = QRectF(14, rect.center().y() - 4.5, 9, 9)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.ACCENT if self._stretched else theme.TEXT_MUTED))
        painter.drawEllipse(dot)

        painter.setPen(QColor(theme.TEXT))
        painter.drawText(rect.adjusted(30, 0, -12, 0), Qt.AlignVCenter | Qt.AlignLeft, self._text())
        painter.end()
