"""Start page: pick a monitor, set color and resolution for the desktop."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from ..engine import Engine
from ..winapi import displays
from . import theme
from .panels import ColorPanel, ResolutionPanel
from .widgets import Badge, Card, Toggle, label


class DisplayPage(QWidget):
    """Everything that takes effect on the desktop right away."""

    statusMessage = Signal(str)

    def __init__(self, engine: Engine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.store = engine.store
        self._displays: list[displays.Display] = []
        # While the interface is being filled, nothing may be written back.
        self._loading = True
        self._live_timer = QTimer(self)
        self._live_timer.setSingleShot(True)
        self._live_timer.setInterval(120)
        self._live_timer.timeout.connect(self._apply_live)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        head = QVBoxLayout()
        head.setSpacing(4)
        title = label("Display", "pageTitle")
        hint = label("Color and resolution for the desktop. These values apply whenever "
                     "no game profile is active.", "pageHint")
        head.addWidget(title)
        head.addWidget(hint)
        outer.addLayout(head)

        selector = QWidget()
        selector_layout = QHBoxLayout(selector)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.setSpacing(8)
        self.display_box = QComboBox()
        self.display_box.setMinimumWidth(280)
        self.display_box.currentIndexChanged.connect(self._on_display_changed)
        self.refresh_button = QPushButton("Rescan")
        self.refresh_button.setObjectName("ghost")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(self.reload_displays)
        selector_layout.addWidget(self.display_box, 1)
        selector_layout.addWidget(self.refresh_button)
        outer.addWidget(selector)

        self.capability_card = Card("Available control")
        self.capability_badges = QHBoxLayout()
        self.capability_badges.setSpacing(8)
        self.badge_vibrance = Badge("Vibrance", theme.TEXT_MUTED)
        self.badge_gamma = Badge("Gamma", theme.TEXT_MUTED)
        self.badge_resolution = Badge("Resolution", theme.TEXT_MUTED)
        self.badge_ddcci = Badge("DDC/CI", theme.TEXT_MUTED)
        for badge in (self.badge_vibrance, self.badge_gamma, self.badge_resolution, self.badge_ddcci):
            self.capability_badges.addWidget(badge)
        self.capability_badges.addStretch(1)
        holder = QWidget()
        holder.setLayout(self.capability_badges)
        self.capability_card.add(holder)
        self.capability_note = label("", "faint")
        self.capability_card.add(self.capability_note)
        outer.addWidget(self.capability_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(16)

        self.color_panel = ColorPanel("Color", "")
        self.resolution_panel = ResolutionPanel("Resolution", "", store=self.store)
        content_layout.addWidget(self.color_panel)
        content_layout.addWidget(self.resolution_panel)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.live_toggle = Toggle("Apply live", True)
        self.live_toggle.setToolTip("Put changes on the monitor as you move the sliders")
        self.apply_button = QPushButton("Apply")
        self.apply_button.setObjectName("primary")
        self.apply_button.setCursor(Qt.PointingHandCursor)
        self.apply_button.clicked.connect(self.apply_now)
        self.reset_button = QPushButton("Reset everything")
        self.reset_button.setObjectName("ghost")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self.reset_all)
        actions_layout.addWidget(self.live_toggle)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.reset_button)
        actions_layout.addWidget(self.apply_button)
        outer.addWidget(actions)

        self.color_panel.changed.connect(self._on_changed)
        self.resolution_panel.changed.connect(self._on_changed)

        self.reload_displays()
        self.load_from_store()
        self.update_capabilities()
        self._loading = False

    # -- Monitors -----------------------------------------------------
    def reload_displays(self) -> None:
        self._displays = displays.list_displays()
        current = self.display_box.currentData()
        self.display_box.blockSignals(True)
        self.display_box.clear()
        for display in self._displays:
            self.display_box.addItem(display.label, display.device)
        self.display_box.blockSignals(False)
        if current:
            index = self.display_box.findData(current)
            if index >= 0:
                self.display_box.setCurrentIndex(index)
        self._on_display_changed(self.display_box.currentIndex())

    def current_display(self) -> displays.Display | None:
        device = self.display_box.currentData()
        return next((d for d in self._displays if d.device == device), None)

    def _on_display_changed(self, _index: int) -> None:
        display = self.current_display()
        self.resolution_panel.set_display(display)
        if self._loading:
            return
        if display is not None:
            desktop = self.store.settings.desktop
            desktop.display = display.device
            self.store.save_settings()

    # -- Capabilities -------------------------------------------------
    def update_capabilities(self) -> None:
        caps = self.engine.capabilities
        self.badge_vibrance.set_state(
            "Digital vibrance" if caps.vibrance_ok else "no vibrance",
            theme.SUCCESS if caps.vibrance_ok else theme.TEXT_FAINT)
        self.badge_gamma.set_state(
            "Brightness, contrast, gamma" if caps.gamma_ok else "gamma ramp blocked",
            theme.SUCCESS if caps.gamma_ok else theme.WARNING)
        self.badge_resolution.set_state("Resolution", theme.SUCCESS)
        self.badge_ddcci.set_state(
            "Monitor over DDC/CI" if caps.ddcci_ok else "no DDC/CI",
            theme.SUCCESS if caps.ddcci_ok else theme.TEXT_FAINT)

        notes = []
        if caps.driver:
            notes.append(f"NVIDIA {caps.driver}")
        if not caps.gamma_ok and caps.gamma_reason:
            notes.append(caps.gamma_reason)
        if not caps.vibrance_ok and caps.vibrance_reason:
            notes.append(caps.vibrance_reason)
        self.capability_note.setText("   ".join(notes))
        self.color_panel.set_capabilities(caps.gamma_ok, caps.gamma_reason,
                                          caps.vibrance_ok, caps.vibrance_reason)

    # -- Values -------------------------------------------------------
    def load_from_store(self) -> None:
        desktop = self.store.settings.desktop
        self.color_panel.set_values(desktop.color)
        self.resolution_panel.set_values(desktop.resolution)
        if desktop.display and desktop.display != "primary":
            index = self.display_box.findData(desktop.display)
            if index >= 0:
                self.display_box.setCurrentIndex(index)

    def _collect(self) -> None:
        desktop = self.store.settings.desktop
        desktop.color = self.color_panel.values()
        desktop.resolution = self.resolution_panel.values()
        desktop.display = self.display_box.currentData() or "primary"
        self.store.save_settings()

    def _on_changed(self) -> None:
        if self._loading:
            return
        self._collect()
        if self.live_toggle.isChecked():
            self._live_timer.start()

    def _apply_live(self) -> None:
        if self.engine.active is not None:
            self.statusMessage.emit(
                f"{self.engine.active.name} is running, desktop values apply afterwards")
            return
        self.apply_now(quiet=True)

    def apply_now(self, quiet: bool = False) -> None:
        self._collect()
        desktop = self.store.settings.desktop
        device = desktop.display
        notes: list[str] = []
        if desktop.color.enabled:
            notes += self.engine.apply_color(device, desktop.color)
        if desktop.resolution.is_set():
            notes += self.engine.apply_resolution(device, desktop.resolution)
            self.reload_displays()
        if notes:
            self.statusMessage.emit(notes[0])
        elif not quiet:
            self.statusMessage.emit("Applied")

    def reset_all(self) -> None:
        self.engine.restore_all()
        self.color_panel.reset()
        self.reload_displays()
        self.statusMessage.emit("Original state restored")
