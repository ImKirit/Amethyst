"""Reusable building blocks of the interface."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication, QCheckBox,
                               QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import theme


class Card(QFrame):
    """A raised surface with a title and an optional hint."""

    def __init__(self, title: str = "", hint: str = "", flat: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFlat" if flat else "card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 20)
        self._layout.setSpacing(12)
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        if title:
            label = QLabel(title)
            label.setObjectName("cardTitle")
            self.header.addWidget(label)
            self.header.addStretch(1)
            self._layout.addLayout(self.header)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("cardHint")
            hint_label.setWordWrap(True)
            self._layout.addWidget(hint_label)

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)

    def add_header_widget(self, widget: QWidget) -> QWidget:
        self.header.addWidget(widget)
        return widget

    def body(self) -> QVBoxLayout:
        return self._layout


class SliderRow(QWidget):
    """Labelled slider with a value readout; double click resets it."""

    valueChanged = Signal(float)

    def __init__(self, label: str, minimum: float, maximum: float, default: float,
                 step: float = 1.0, suffix: str = "", decimals: int = 0,
                 hint: str = "", parent=None) -> None:
        super().__init__(parent)
        self._min, self._max, self._step = minimum, maximum, step
        self._default = default
        self._suffix = suffix
        self._decimals = decimals

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(label)
        self.title.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.value_label = QLabel()
        self.value_label.setObjectName("valueLabel")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.value_label)
        outer.addLayout(top)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(round(minimum / step)))
        self.slider.setMaximum(int(round(maximum / step)))
        self.slider.setSingleStep(1)
        self.slider.setPageStep(max(1, int(round((maximum - minimum) / step / 20))))
        self.slider.valueChanged.connect(self._on_change)
        outer.addWidget(self.slider)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("faint")
            outer.addWidget(hint_label)

        self.set_value(default)

    def _on_change(self, raw: int) -> None:
        self.value_label.setText(self._format(self.value()))
        self.valueChanged.emit(self.value())

    def _format(self, value: float) -> str:
        text = f"{value:.{self._decimals}f}"
        if self._decimals == 0 and self._min < 0:
            text = f"{value:+.0f}"
        return f"{text}{self._suffix}"

    def value(self) -> float:
        return self.slider.value() * self._step

    def set_value(self, value: float) -> None:
        blocked = self.slider.blockSignals(True)
        self.slider.setValue(int(round(value / self._step)))
        self.slider.blockSignals(blocked)
        self.value_label.setText(self._format(self.value()))

    def reset(self) -> None:
        self.set_value(self._default)
        self.valueChanged.emit(self.value())

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.reset()
        super().mouseDoubleClickEvent(event)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - Qt naming
        super().setEnabled(enabled)
        self.title.setStyleSheet(
            "font-size: 12px; font-weight: 500;" if enabled
            else f"font-size: 12px; font-weight: 500; color: {theme.TEXT_FAINT};")


class Toggle(QCheckBox):
    """Sliding switch: pill with a knob, drawn by hand."""

    TRACK_W = 44
    TRACK_H = 24
    GAP = 11

    def __init__(self, text: str = "", checked: bool = False, parent=None) -> None:
        super().__init__(text, parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QCheckBox::indicator { width: 0px; height: 0px; }")

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        base = super().sizeHint()
        return QSize(base.width() + self.TRACK_W + self.GAP, max(base.height(), self.TRACK_H + 4))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        top = (self.height() - self.TRACK_H) / 2
        track = QRectF(0, top, self.TRACK_W, self.TRACK_H)
        on = self.isChecked()
        enabled = self.isEnabled()

        if on:
            color = QColor(theme.ACCENT) if enabled else QColor(theme.ACCENT_DIM)
        else:
            color = QColor(theme.SURFACE_3)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(track, self.TRACK_H / 2, self.TRACK_H / 2)

        knob_size = self.TRACK_H - 8
        knob_x = track.right() - knob_size - 4 if on else track.left() + 4
        knob = QRectF(knob_x, top + 4, knob_size, knob_size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#F6F1FF" if on else theme.TEXT_MUTED)))
        painter.drawEllipse(knob)

        if self.text():
            painter.setPen(QColor(theme.TEXT if enabled else theme.TEXT_FAINT))
            font = painter.font()
            font.setPointSizeF(9.0)
            painter.setFont(font)
            text_rect = QRectF(self.TRACK_W + self.GAP, 0,
                               self.width() - self.TRACK_W - self.GAP, self.height())
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.text())
        painter.end()

    def hitButton(self, position) -> bool:  # noqa: N802 - Qt naming
        return self.rect().contains(position)


class Badge(QLabel):
    """Small status pill with text."""

    def __init__(self, text: str = "", color: str = theme.TEXT_MUTED, parent=None) -> None:
        super().__init__(text, parent)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self._color = color
        self.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600;"
            f" background: rgba(255,255,255,0.07); border-radius: 11px;"
            f" padding: 5px 12px;")

    def set_state(self, text: str, color: str) -> None:
        self.setText(text)
        self.set_color(color)


class IconButton(QPushButton):
    def __init__(self, glyph: str, tooltip: str = "", parent=None) -> None:
        super().__init__(glyph, parent)
        self.setObjectName("windowButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(34, 30)
        if tooltip:
            self.setToolTip(tooltip)


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return line


def row(*widgets: QWidget, spacing: int = 8) -> QWidget:
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        if widget is None:
            layout.addStretch(1)
        else:
            layout.addWidget(widget)
    return holder


def label(text: str, kind: str = "") -> QLabel:
    item = QLabel(text)
    if kind:
        item.setObjectName(kind)
    item.setWordWrap(True)
    return item


class ColorPreview(QWidget):
    """Swatch strip that roughly shows the configured color values."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(70)
        self._brightness = 0.0
        self._contrast = 50.0
        self._gamma = 1.0
        self._vibrance = 50
        self._gains = (100.0, 100.0, 100.0)

    def update_values(self, brightness: float, contrast: float, gamma_value: float,
                      vibrance: int, gains: tuple[float, float, float]) -> None:
        self._brightness = brightness
        self._contrast = contrast
        self._gamma = gamma_value
        self._vibrance = vibrance
        self._gains = gains
        self.update()

    def _transform(self, r: float, g: float, b: float) -> tuple[int, int, int]:
        offset = self._brightness / 100.0
        factor = self._contrast / 50.0
        inv_gamma = 1.0 / max(0.01, self._gamma)
        saturation = 1.0 + (self._vibrance - 50) / 50.0
        channels = []
        grey = 0.299 * r + 0.587 * g + 0.114 * b
        for value, gain in zip((r, g, b), self._gains):
            value = grey + (value - grey) * saturation
            value = (value - 0.5) * factor + 0.5 + offset
            value = max(0.0, min(1.0, value)) ** inv_gamma
            value = max(0.0, min(1.0, value * gain / 100.0))
            channels.append(int(round(value * 255)))
        return channels[0], channels[1], channels[2]

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        painter.setClipPath(path)

        swatches = [
            (0.05, 0.05, 0.05), (0.35, 0.35, 0.35), (0.75, 0.75, 0.75),
            (0.85, 0.15, 0.20), (0.20, 0.75, 0.35), (0.25, 0.45, 0.95),
            (0.95, 0.80, 0.20), (0.65, 0.30, 0.90),
        ]
        width = rect.width() / len(swatches)
        for index, (r, g, b) in enumerate(swatches):
            cr, cg, cb = self._transform(r, g, b)
            painter.fillRect(QRectF(rect.left() + index * width, rect.top(), width + 1, rect.height()),
                             QColor(cr, cg, cb))
        painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawPath(path)
        painter.end()


def app_icon(size: int = 256) -> QIcon:
    """App icon: a cut crystal in violet."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    s = size / 256.0
    body = QPainterPath()
    body.moveTo(128 * s, 18 * s)
    body.lineTo(226 * s, 92 * s)
    body.lineTo(188 * s, 232 * s)
    body.lineTo(68 * s, 232 * s)
    body.lineTo(30 * s, 92 * s)
    body.closeSubpath()

    gradient = QLinearGradient(QPointF(40 * s, 20 * s), QPointF(210 * s, 240 * s))
    gradient.setColorAt(0.0, QColor("#C77DFF"))
    gradient.setColorAt(0.5, QColor("#A855F7"))
    gradient.setColorAt(1.0, QColor("#6D28D9"))
    painter.fillPath(body, QBrush(gradient))

    facet = QPainterPath()
    facet.moveTo(128 * s, 18 * s)
    facet.lineTo(30 * s, 92 * s)
    facet.lineTo(128 * s, 232 * s)
    facet.closeSubpath()
    painter.fillPath(facet, QColor(255, 255, 255, 38))

    shine = QPainterPath()
    shine.moveTo(128 * s, 18 * s)
    shine.lineTo(226 * s, 92 * s)
    shine.lineTo(160 * s, 108 * s)
    shine.closeSubpath()
    painter.fillPath(shine, QColor(255, 255, 255, 70))

    painter.setPen(QPen(QColor("#E9D5FF"), 3 * s))
    painter.drawPath(body)
    painter.end()
    return QIcon(pixmap)


def wordmark_font(size: int = 19) -> QFont:
    font = QFont(theme.FONT, size)
    font.setWeight(QFont.Bold)
    font.setLetterSpacing(QFont.PercentageSpacing, 102)
    return font


def connect_all(widgets: list[SliderRow], handler: Callable[[float], None]) -> None:
    for widget in widgets:
        widget.valueChanged.connect(handler)

class WheelGuard(QObject):
    """Keeps the mouse wheel from changing sliders and dropdowns.

    Scrolling over a control used to change its value, which is easy to do by
    accident while reading a page. The event is handed to the surrounding
    scroll area instead, so the wheel scrolls the page like everywhere else.
    """

    TARGETS = (QSlider, QComboBox, QAbstractSpinBox)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt naming
        if event.type() != QEvent.Type.Wheel or not isinstance(obj, self.TARGETS):
            return False
        if isinstance(obj, QComboBox) and obj.view().isVisible():
            return False          # the open dropdown list may scroll
        area = self._scroll_area(obj)
        if area is not None:
            QApplication.sendEvent(area.viewport(), event)
        return True

    @staticmethod
    def _scroll_area(widget) -> QAbstractScrollArea | None:
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                return parent
            parent = parent.parentWidget()
        return None
