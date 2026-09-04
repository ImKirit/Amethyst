"""The two setting blocks: color and resolution.

Both are used twice: once for the desktop on the start page and once in the
profile editor. They only know their values, not the app.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..models import ColorSettings, ResolutionSettings
from ..presets import STRETCHED_HINTS
from ..winapi.displays import Display
from . import theme
from .widgets import Badge, Card, ColorPreview, SliderRow, Toggle, label


class ColorPanel(Card):
    """Sliders for vibrance, brightness, contrast, gamma and channel balance."""

    changed = Signal()

    def __init__(self, title: str = "Color", hint: str = "", parent=None) -> None:
        super().__init__(title, hint, parent=parent)
        self.toggle = Toggle("on", True)
        self.toggle.setToolTip("Whether this profile touches the colors at all")
        self.add_header_widget(self.toggle)

        self.notice = label("", "faint")
        self.notice.hide()
        self.add(self.notice)

        self.preview = ColorPreview()
        self.add(self.preview)

        self.vibrance = SliderRow("Digital vibrance", 0, 100, 50, 1, " %",
                                  hint="50 matches the normal Windows saturation")
        self.brightness = SliderRow("Brightness", -50, 50, 0, 1, " %")
        self.contrast = SliderRow("Contrast", 0, 100, 50, 1, " %")
        self.gamma = SliderRow("Gamma", 0.30, 2.80, 1.00, 0.01, "", decimals=2)
        for slider in (self.vibrance, self.brightness, self.contrast, self.gamma):
            self.add(slider)

        self.channel_header = label("Color balance", "cardHint")
        self.add(self.channel_header)
        self.red = SliderRow("Red", 50, 150, 100, 1, " %")
        self.green = SliderRow("Green", 50, 150, 100, 1, " %")
        self.blue = SliderRow("Blue", 50, 150, 100, 1, " %")
        for slider in (self.red, self.green, self.blue):
            self.add(slider)

        self.reset_button = QPushButton("Reset to default")
        self.reset_button.setObjectName("ghost")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self.reset)
        self.add(self.reset_button)

        for slider in self._sliders():
            slider.valueChanged.connect(self._emit)
        self.toggle.toggled.connect(self._on_toggle)
        self._update_preview()

    def _sliders(self) -> list[SliderRow]:
        return [self.vibrance, self.brightness, self.contrast, self.gamma,
                self.red, self.green, self.blue]

    def _on_toggle(self, checked: bool) -> None:
        for slider in self._sliders():
            slider.setEnabled(checked)
        self.preview.setEnabled(checked)
        self.changed.emit()

    def _emit(self, *_args) -> None:
        self._update_preview()
        self.changed.emit()

    def _update_preview(self) -> None:
        self.preview.update_values(
            self.brightness.value(), self.contrast.value(), self.gamma.value(),
            int(self.vibrance.value()),
            (self.red.value(), self.green.value(), self.blue.value()))

    def set_capabilities(self, gamma_ok: bool, gamma_reason: str,
                         vibrance_ok: bool, vibrance_reason: str) -> None:
        """Grey out what is not available and say why."""
        messages = []
        for slider in (self.brightness, self.contrast, self.gamma, self.red, self.green, self.blue):
            slider.setEnabled(gamma_ok and self.toggle.isChecked())
        self.vibrance.setEnabled(vibrance_ok and self.toggle.isChecked())
        if not gamma_ok and gamma_reason:
            messages.append(gamma_reason)
        if not vibrance_ok and vibrance_reason:
            messages.append(vibrance_reason)
        if messages:
            self.notice.setText("  ".join(messages))
            self.notice.setStyleSheet(f"color: {theme.WARNING}; font-size: 11px;")
            self.notice.show()
        else:
            self.notice.hide()

    # -- Values -------------------------------------------------------
    def values(self) -> ColorSettings:
        return ColorSettings(
            enabled=self.toggle.isChecked(),
            brightness=self.brightness.value(),
            contrast=self.contrast.value(),
            gamma=self.gamma.value(),
            vibrance=int(self.vibrance.value()),
            red=self.red.value(),
            green=self.green.value(),
            blue=self.blue.value(),
        )

    def set_values(self, color: ColorSettings) -> None:
        blocked = self.blockSignals(True)
        self.toggle.setChecked(color.enabled)
        self.vibrance.set_value(color.vibrance)
        self.brightness.set_value(color.brightness)
        self.contrast.set_value(color.contrast)
        self.gamma.set_value(color.gamma)
        self.red.set_value(color.red)
        self.green.set_value(color.green)
        self.blue.set_value(color.blue)
        for slider in self._sliders():
            slider.setEnabled(color.enabled)
        self.blockSignals(blocked)
        self._update_preview()

    def reset(self) -> None:
        neutral = ColorSettings.neutral()
        neutral.enabled = self.toggle.isChecked()
        self.set_values(neutral)
        self.changed.emit()


class ResolutionPanel(Card):
    """Picks resolution and refresh rate, stretched modes included."""

    changed = Signal()

    def __init__(self, title: str = "Resolution", hint: str = "", store=None,
                 parent=None) -> None:
        super().__init__(title, hint, parent=parent)
        self.toggle = Toggle("on", False)
        self.toggle.setToolTip("Whether this profile switches the resolution")
        self.add_header_widget(self.toggle)

        self.store = store
        self._display: Display | None = None

        line = QWidget()
        layout = QHBoxLayout(line)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.resolution_box = QComboBox()
        self.resolution_box.setMinimumWidth(180)
        self.refresh_box = QComboBox()
        self.refresh_box.setMinimumWidth(96)
        layout.addWidget(self.resolution_box, 3)
        layout.addWidget(self.refresh_box, 1)
        self.add(line)

        status = QWidget()
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        self.aspect_badge = Badge("", theme.TEXT_MUTED)
        self.native_label = QLabel()
        self.native_label.setObjectName("faint")
        status_layout.addWidget(self.aspect_badge)
        status_layout.addWidget(self.native_label)
        status_layout.addStretch(1)

        self.create_button = QPushButton("Create preset")
        self.create_button.setObjectName("ghost")
        self.create_button.setCursor(Qt.PointingHandCursor)
        self.create_button.setToolTip("Add a resolution of your own, for example a stretched one")
        self.create_button.clicked.connect(self._create_preset)
        self.delete_button = QPushButton("Delete preset")
        self.delete_button.setObjectName("ghost")
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self._delete_preset)
        self.delete_button.hide()
        status_layout.addWidget(self.delete_button)
        status_layout.addWidget(self.create_button)
        self.add(status)

        self.stretch_hint = label(
            "The picture only stretches once the scaling mode in the graphics driver is set "
            "to full-screen and the GPU performs the scaling. On NVIDIA: Control Panel, "
            "Adjust desktop size and position.", "faint")
        self.add(self.stretch_hint)

        self.resolution_box.currentIndexChanged.connect(self._on_resolution)
        self.refresh_box.currentIndexChanged.connect(lambda _i: self.changed.emit())
        self.toggle.toggled.connect(self._on_toggle)
        self._on_toggle(self.toggle.isChecked())

    def _on_toggle(self, checked: bool) -> None:
        self.resolution_box.setEnabled(checked)
        self.refresh_box.setEnabled(checked)
        self.changed.emit()

    def set_display(self, display: Display | None) -> None:
        self._display = display
        current = self.values()
        self.resolution_box.blockSignals(True)
        self.resolution_box.clear()

        # own presets first, they are the reason someone opens this list
        if self.store is not None and display is not None:
            for mode in self.store.modes_for(display.device):
                self.resolution_box.addItem(f"{mode.label()}   own",
                                            (mode.width, mode.height, mode.refresh))

        if display is not None:
            native = display.native_aspect()
            for width, height in display.resolutions():
                aspect = width / height if height else 0
                tag = ""
                if abs(aspect - native) > 0.02:
                    tag = "  stretched" if (width, height) in STRETCHED_HINTS else "  other ratio"
                self.resolution_box.addItem(f"{width} x {height}{tag}", (width, height, 0))
            self.native_label.setText(
                f"native {display.current.width} x {display.current.height} "
                f"@ {display.current.refresh} Hz")
        self.resolution_box.blockSignals(False)
        if current.width:
            self.select(current.width, current.height, current.refresh)
        else:
            self._on_resolution(self.resolution_box.currentIndex())

    def _create_preset(self) -> None:
        from .preset_dialog import PresetDialog          # noqa: PLC0415 - avoids a cycle

        if self.store is None or self._display is None:
            return
        dialog = PresetDialog(self._display.device, self.window())
        if dialog.exec() != PresetDialog.Accepted:
            return
        preset = dialog.preset()
        self.store.add_custom_mode(preset)
        self.set_display(self._display)
        self.select(preset.width, preset.height, preset.refresh)
        self.toggle.setChecked(True)
        self.changed.emit()

    def _delete_preset(self) -> None:
        if self.store is None or self._display is None:
            return
        data = self.resolution_box.currentData()
        if not data:
            return
        width, height, refresh = data
        for mode in self.store.modes_for(self._display.device):
            if (mode.width, mode.height, mode.refresh) == (width, height, refresh):
                self.store.remove_custom_mode(mode)
                break
        self.set_display(self._display)
        self.changed.emit()

    def _on_resolution(self, index: int) -> None:
        data = self.resolution_box.itemData(index)
        self.refresh_box.blockSignals(True)
        self.refresh_box.clear()
        own = bool(data) and data[2] != 0
        self.delete_button.setVisible(own)
        if data and self._display:
            width, height, own_rate = data
            rates = self._display.refresh_rates(width, height)
            if own_rate and own_rate not in rates:
                rates = sorted({own_rate, *rates}, reverse=True)
            for rate in rates:
                self.refresh_box.addItem(f"{rate} Hz", rate)
            if own_rate:
                position = self.refresh_box.findData(own_rate)
                if position >= 0:
                    self.refresh_box.setCurrentIndex(position)
            native = self._display.native_aspect()
            aspect = width / height if height else 0
            if abs(aspect - native) > 0.02:
                self.aspect_badge.set_state("stretched", theme.ACCENT)
                self.stretch_hint.show()
            else:
                self.aspect_badge.set_state("native ratio", theme.SUCCESS)
                self.stretch_hint.hide()
        self.refresh_box.blockSignals(False)
        self.changed.emit()

    def select(self, width: int, height: int, refresh: int) -> None:
        exact = -1
        fallback = -1
        for index in range(self.resolution_box.count()):
            data = self.resolution_box.itemData(index)
            if not data or (data[0], data[1]) != (width, height):
                continue
            if data[2] == refresh and exact < 0:
                exact = index
            if fallback < 0:
                fallback = index
        chosen = exact if exact >= 0 else fallback
        if chosen >= 0:
            self.resolution_box.setCurrentIndex(chosen)
        for index in range(self.refresh_box.count()):
            if self.refresh_box.itemData(index) == refresh:
                self.refresh_box.setCurrentIndex(index)
                break

    def values(self) -> ResolutionSettings:
        data = self.resolution_box.currentData()
        rate = self.refresh_box.currentData()
        if not data:
            return ResolutionSettings(enabled=self.toggle.isChecked())
        width, height = data[0], data[1]
        return ResolutionSettings(enabled=self.toggle.isChecked(), width=width, height=height,
                                  refresh=int(rate or 0))

    def set_values(self, resolution: ResolutionSettings) -> None:
        self.toggle.setChecked(resolution.enabled)
        if resolution.width:
            self.select(resolution.width, resolution.height, resolution.refresh)
