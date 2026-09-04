"""Tray icon with the most important commands."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import APP_NAME
from ..engine import Engine
from .widgets import app_icon


class Tray(QSystemTrayIcon):
    def __init__(self, window, engine: Engine) -> None:
        super().__init__(app_icon(), window)
        self.window = window
        self.engine = engine
        self.setToolTip(APP_NAME)
        self.activated.connect(self._on_activated)

        self.menu = QMenu()
        self.menu.setStyleSheet(window.styleSheet())
        self.menu.aboutToShow.connect(self._rebuild)
        self.setContextMenu(self.menu)
        self._rebuild()

    def _rebuild(self) -> None:
        self.menu.clear()
        status = QAction(self.engine.status_text(), self.menu)
        status.setEnabled(False)
        self.menu.addAction(status)
        self.menu.addSeparator()

        open_action = QAction("Open window", self.menu)
        open_action.triggered.connect(self._show_window)
        self.menu.addAction(open_action)

        if self.engine.store.profiles:
            submenu = self.menu.addMenu("Apply profile")
            for profile in self.engine.store.profiles:
                action = QAction(f"{profile.icon}  {profile.name}", submenu)
                action.triggered.connect(lambda _c=False, p=profile: self.engine.activate(p))
                submenu.addAction(action)

        reset = QAction("Reset everything", self.menu)
        reset.triggered.connect(self.engine.restore_all)
        self.menu.addAction(reset)

        self.menu.addSeparator()
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.window.quit_app)
        self.menu.addAction(quit_action)

    def _show_window(self) -> None:
        self.window.bring_to_front()

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.window.isVisible():
                self.window.hide()
            else:
                self._show_window()

    def notify(self, title: str, message: str) -> None:
        if self.supportsMessages():
            self.showMessage(title, message, app_icon(), 2500)
