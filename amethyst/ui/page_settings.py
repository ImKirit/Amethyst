"""Settings, diagnostics and information about the program."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .. import APP_NAME, REPO_URL, VERSION
from ..engine import Engine
from ..paths import data_dir
from ..winapi import autostart, gamma
from . import theme
from .widgets import Card, SliderRow, Toggle, label


class SettingsPage(QWidget):
    """Everything you set once and then forget."""

    statusMessage = Signal(str)
    intervalChanged = Signal(float)

    def __init__(self, engine: Engine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.store = engine.store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(label("Settings", "pageTitle"))
        head.addWidget(label("How Amethyst behaves, plus a diagnosis of the interfaces.",
                             "pageHint"))
        outer.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)

        # -- behaviour
        behaviour = Card("Behaviour")
        settings = self.store.settings
        self.autostart_toggle = Toggle("Start with Windows", autostart.is_enabled())
        self.autostart_toggle.toggled.connect(self._on_autostart)
        self.minimized_toggle = Toggle("Start minimized", settings.start_minimized)
        self.tray_toggle = Toggle("Closing hides to the tray", settings.close_to_tray)
        self.notify_toggle = Toggle("Short notice when a profile switches", settings.notifications)
        for toggle in (self.minimized_toggle, self.tray_toggle, self.notify_toggle):
            toggle.toggled.connect(self._save)
        for toggle in (self.autostart_toggle, self.minimized_toggle,
                       self.tray_toggle, self.notify_toggle):
            behaviour.add(toggle)

        self.interval = SliderRow("Check interval", 0.5, 10.0, settings.poll_seconds, 0.5,
                                  " s", decimals=1,
                                  hint="How often Amethyst looks for running games")
        self.interval.valueChanged.connect(self._on_interval)
        behaviour.add(self.interval)
        layout.addWidget(behaviour)

        # -- brightness source
        source = Card("Path for brightness and contrast",
                      "Normally the gamma ramp of the graphics card handles this. When it is "
                      "blocked, Amethyst can drive the monitor menu over DDC/CI instead.")
        self.source_box = QComboBox()
        self.source_box.addItem("Choose automatically", "auto")
        self.source_box.addItem("Gamma ramp only", "gamma")
        self.source_box.addItem("Monitor only (DDC/CI)", "ddcci")
        index = self.source_box.findData(settings.brightness_source)
        self.source_box.setCurrentIndex(index if index >= 0 else 0)
        self.source_box.currentIndexChanged.connect(self._save)
        source.add(self.source_box)
        layout.addWidget(source)

        # -- system
        system = Card("System",
                      "Windows clamps the gamma ramp until the extended range is unlocked. "
                      "That is a registry value and needs administrator rights.")
        self.gamma_state = label("", "faint")
        system.add(self.gamma_state)
        unlock_row = QHBoxLayout()
        self.unlock_button = QPushButton("Unlock the full gamma range")
        self.unlock_button.setObjectName("ghost")
        self.unlock_button.setCursor(Qt.PointingHandCursor)
        self.unlock_button.clicked.connect(self._unlock_gamma)
        unlock_row.addWidget(self.unlock_button)
        unlock_row.addStretch(1)
        system.add_layout(unlock_row)
        layout.addWidget(system)

        # -- diagnostics
        self.diagnostics = Card("Diagnostics")
        self.diagnostics_text = label("", "muted")
        self.diagnostics.add(self.diagnostics_text)
        diag_row = QHBoxLayout()
        recheck = QPushButton("Check again")
        recheck.setObjectName("ghost")
        recheck.setCursor(Qt.PointingHandCursor)
        recheck.clicked.connect(self.refresh)
        folder = QPushButton("Open data folder")
        folder.setObjectName("ghost")
        folder.setCursor(Qt.PointingHandCursor)
        folder.clicked.connect(self._open_folder)
        diag_row.addWidget(recheck)
        diag_row.addWidget(folder)
        diag_row.addStretch(1)
        self.diagnostics.add_layout(diag_row)
        layout.addWidget(self.diagnostics)

        # -- about
        about = Card("About")
        about.add(label(f"{APP_NAME} {VERSION}", "cardTitle"))
        about.add(label("Per-game color and resolution profiles for Windows.", "muted"))
        link = QPushButton("Open the project page")
        link.setObjectName("ghost")
        link.setCursor(Qt.PointingHandCursor)
        link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))
        about.add(link)
        layout.addWidget(about)

        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.refresh()

    # -- actions ------------------------------------------------------
    def _save(self, *_args) -> None:
        settings = self.store.settings
        settings.start_minimized = self.minimized_toggle.isChecked()
        settings.close_to_tray = self.tray_toggle.isChecked()
        settings.notifications = self.notify_toggle.isChecked()
        settings.brightness_source = self.source_box.currentData() or "auto"
        self.store.save_settings()

    def _on_interval(self, value: float) -> None:
        self.store.settings.poll_seconds = value
        self.store.save_settings()
        self.intervalChanged.emit(value)

    def _on_autostart(self, checked: bool) -> None:
        ok, message = autostart.set_enabled(checked)
        self.statusMessage.emit(message)
        if not ok:
            self.autostart_toggle.blockSignals(True)
            self.autostart_toggle.setChecked(not checked)
            self.autostart_toggle.blockSignals(False)

    def _unlock_gamma(self) -> None:
        ok, message = gamma.unlock_gamma_range()
        self.statusMessage.emit(message)
        self.refresh()

    def _open_folder(self) -> None:
        path = str(data_dir())
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 - intended: open Explorer
        else:  # pragma: no cover - Windows only
            subprocess.Popen(["xdg-open", path])

    def refresh(self) -> None:
        caps = self.engine.refresh_capabilities()
        unlocked = caps.gamma_range_unlocked
        self.gamma_state.setText(
            "The extended range is unlocked." if unlocked
            else "The extended range is locked, strong values will be clamped.")
        self.gamma_state.setStyleSheet(
            f"color: {theme.SUCCESS if unlocked else theme.WARNING}; font-size: 11px;")
        self.unlock_button.setEnabled(not unlocked)

        lines = [
            f"Windows: {sys.getwindowsversion().major}.{sys.getwindowsversion().minor} "
            f"build {sys.getwindowsversion().build}",
            f"NVAPI: {caps.driver or 'not available'}"
            + ("" if caps.vibrance_ok else f" ({caps.vibrance_reason})"),
            f"Gamma ramp: {'available' if caps.gamma_ok else 'blocked'}"
            + ("" if caps.gamma_ok else f" ({caps.gamma_reason})"),
            f"DDC/CI: {', '.join(caps.ddcci_devices) if caps.ddcci_devices else caps.ddcci_reason or 'no answer from the monitor'}",
            f"Data folder: {data_dir()}",
        ]
        self.diagnostics_text.setText("\n".join(lines))
