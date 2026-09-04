"""Dialog for adding a resolution by hand.

Not every mode a monitor can take is in the driver list, and stretched setups
often need one that is not. Type it in, and Amethyst asks the driver whether
it would accept it before saving.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from ..models import CustomMode
from ..winapi import displays
from . import theme
from .widgets import label


class PresetDialog(QDialog):
    """Name, width, height and refresh rate, with a live check."""

    def __init__(self, device: str, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.setWindowTitle("Create preset")
        self.setMinimumWidth(420)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        layout.addWidget(label("A resolution of your own. It shows up in the dropdown of every "
                               "profile on this display.", "pageHint"))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name, for example Stretched 4:3")
        layout.addWidget(self.name_edit)

        fields = QWidget()
        row = QHBoxLayout(fields)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.width_box = self._number(640, 7680, 1440, " px")
        self.height_box = self._number(480, 4320, 1080, " px")
        self.refresh_box = self._number(24, 500, 240, " Hz")
        for caption, box in (("Width", self.width_box), ("Height", self.height_box),
                             ("Refresh", self.refresh_box)):
            column = QVBoxLayout()
            column.setSpacing(5)
            title = QLabel(caption)
            title.setObjectName("cardHint")
            column.addWidget(title)
            column.addWidget(box)
            row.addLayout(column)
        layout.addWidget(fields)

        current = displays.current_mode(device)
        if current is not None:
            self.refresh_box.setValue(current.refresh)
        self.status = label("", "faint")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.check_button = QPushButton("Test")
        self.check_button.setObjectName("ghost")
        self.check_button.setCursor(Qt.PointingHandCursor)
        self.check_button.clicked.connect(self._check)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("ghost")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Save preset")
        self.save_button.setObjectName("primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.check_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        for box in (self.width_box, self.height_box, self.refresh_box):
            box.valueChanged.connect(self._on_change)
        self._check()

    def _number(self, low: int, high: int, value: int, suffix: str) -> QSpinBox:
        box = QSpinBox()
        box.setRange(low, high)
        box.setValue(value)
        box.setSuffix(suffix)
        box.setSingleStep(1)
        box.setButtonSymbols(QSpinBox.NoButtons)
        box.setAlignment(Qt.AlignCenter)
        return box

    def _on_change(self, _value: int) -> None:
        self.status.setText("")
        self._check()

    def _check(self) -> None:
        mode = self.mode()
        if displays.test_mode(self.device, mode):
            self.status.setText(f"The driver accepts {mode.label()}.")
            self.status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 11px;")
            return
        self.status.setText(
            f"The driver refuses {mode.label()}. You can still save it, but it only works "
            "after you add it as a custom resolution in your graphics control panel.")
        self.status.setStyleSheet(f"color: {theme.WARNING}; font-size: 11px;")

    def mode(self) -> displays.DisplayMode:
        return displays.DisplayMode(self.width_box.value(), self.height_box.value(),
                                    self.refresh_box.value())

    def preset(self) -> CustomMode:
        mode = self.mode()
        name = self.name_edit.text().strip()
        return CustomMode(name=name, width=mode.width, height=mode.height, refresh=mode.refresh,
                          device=self.device)
