"""Main window: own title bar on a native Windows frame, pages on the right."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, VERSION
from ..engine import Engine
from ..winapi import window_frame
from . import theme
from .overlay import ResolutionOverlay
from .page_display import DisplayPage
from .page_profiles import ProfilesPage
from .page_settings import SettingsPage
from .titlebar import TitleBar
from .updates import UpdateFlow
from .widgets import app_icon, divider, label, wordmark_font


class MSG(ctypes.Structure):
    _fields_ = [("hWnd", wintypes.HWND), ("message", wintypes.UINT),
                ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t),
                ("time", wintypes.DWORD), ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long)]


class MainWindow(QWidget):
    """The frame around the three pages."""

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self.engine = engine
        self.store = engine.store
        self._force_quit = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        # No Qt frame, but the native window keeps its style, so Windows still
        # snaps, maximizes and resizes it. See winapi/window_frame.py.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setMinimumSize(940, 660)
        self.resize(1080, 780)

        self.root = QWidget(self)
        self.root.setObjectName("root")
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.addWidget(self.root)

        outer = QVBoxLayout(self.root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.title_bar.minimizeRequested.connect(self.showMinimized)
        self.title_bar.maximizeRequested.connect(self.toggle_maximized)
        self.title_bar.closeRequested.connect(self.close)
        outer.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.display_page = DisplayPage(engine)
        self.profiles_page = ProfilesPage(engine)
        self.settings_page = SettingsPage(engine)
        for page in (self.display_page, self.profiles_page, self.settings_page):
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(28, 16, 28, 22)
            holder_layout.addWidget(page)
            self.stack.addWidget(holder)
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)

        for page in (self.display_page, self.profiles_page, self.settings_page):
            page.statusMessage.connect(self.flash)
        self.settings_page.intervalChanged.connect(self._set_interval)
        self.profiles_page.profilesChanged.connect(self._on_profiles_changed)

        self.engine.on_change = self._on_active_changed

        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(lambda: self.title_bar.message.setText(""))

        self.watch_timer = QTimer(self)
        self.watch_timer.timeout.connect(self._tick)
        self._set_interval(self.store.settings.poll_seconds)

        self.overlay = ResolutionOverlay(self.store)
        self.enforce_timer = QTimer(self)
        self.enforce_timer.timeout.connect(self._hold_resolution)
        self.enforce_timer.start(700)

        self.updates = UpdateFlow(self)
        self.updates.nothing.connect(self.flash)
        self.settings_page.checkUpdatesRequested.connect(lambda: self.updates.check(quiet=False))
        self.settings_page.overlayChanged.connect(self._sync_overlay)
        if self.store.settings.check_updates:
            QTimer.singleShot(6000, lambda: self.updates.check(quiet=True))

        self._restore_geometry()

    # -- native frame -------------------------------------------------
    def show(self) -> None:
        super().show()
        window_frame.prepare(int(self.winId()))

    def nativeEvent(self, event_type, message):  # noqa: N802 - Qt naming
        """Let Windows treat this as a normal window, minus the drawn frame."""
        if event_type != b"windows_generic_MSG":
            return False, 0
        msg = MSG.from_address(int(message))

        if msg.message == window_frame.WM_NCCALCSIZE:
            result = window_frame.handle_nccalcsize(msg.lParam, msg.wParam, self.isMaximized())
            return True, result

        if msg.message == window_frame.WM_NCHITTEST:
            ratio = self.devicePixelRatioF() or 1.0
            x = ctypes.c_short(msg.lParam & 0xFFFF).value
            y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
            local = self.mapFromGlobal(QPoint(int(x / ratio), int(y / ratio)))
            in_title = not self.title_bar.is_on_buttons(
                local.x() - self.title_bar.x(), local.y() - self.title_bar.y())
            area = window_frame.hit_test(
                local.x(), local.y(), self.width(), self.height(),
                self.title_bar.height(), in_title, self.isMaximized())
            return True, area

        return False, 0

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            maximized = self.isMaximized()
            self.title_bar.set_maximized(maximized)
            # square corners while maximized, the rounded ones would show the desktop
            self.root.setProperty("maximized", "true" if maximized else "false")
            self.root.style().unpolish(self.root)
            self.root.style().polish(self.root)

    def toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def bring_to_front(self) -> None:
        self.showNormal() if self.isMinimized() else self.show()
        self.raise_()
        self.activateWindow()
        window_frame.to_foreground(int(self.winId()))

    # -- layout -------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(212)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(30, 30))
        brand.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        wordmark = QLabel(APP_NAME)
        wordmark.setObjectName("wordmark")
        wordmark.setFont(wordmark_font())
        tagline = QLabel("Color and resolution profiles")
        tagline.setObjectName("tagline")
        tagline.setWordWrap(True)
        titles.addWidget(wordmark)
        titles.addWidget(tagline)
        brand.addLayout(titles, 1)
        layout.addLayout(brand)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (glyph, text) in enumerate((("🖥️", "Display"), ("🎮", "Profiles"),
                                               ("⚙️", "Settings"))):
            button = QPushButton(f"  {glyph}   {text}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, i=index: self.stack.setCurrentIndex(i))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)
        self.nav_group.button(0).setChecked(True)

        layout.addStretch(1)
        layout.addWidget(divider())
        self.sidebar_status = label("", "faint")
        layout.addWidget(self.sidebar_status)
        version = QLabel(f"Version {VERSION}")
        version.setObjectName("faint")
        layout.addWidget(version)
        return sidebar

    # -- runtime ------------------------------------------------------
    def _set_interval(self, seconds: float) -> None:
        self.watch_timer.start(max(500, int(seconds * 1000)))

    def _tick(self) -> None:
        before, after = self.engine.poll()
        if (before.id if before else None) != (after.id if after else None):
            self.profiles_page.reload()

    def _hold_resolution(self) -> None:
        message = self.engine.enforce_resolution()
        if message:
            self.flash(message)
            self._sync_overlay()

    def _sync_overlay(self) -> None:
        """Show the badge while a profile with a resolution is active."""
        settings = self.store.settings
        profile = self.engine.active
        wanted = profile is not None and profile.resolution.is_set()
        if not (settings.overlay_enabled and wanted):
            self.overlay.hide()
            return
        from ..winapi import displays          # noqa: PLC0415 - keeps the import local

        device = displays.resolve_device(profile.display)
        current = displays.current_mode(device) if device else None
        if current is None:
            self.overlay.hide()
            return
        display = next((d for d in displays.list_displays() if d.device == device), None)
        native = display.native_aspect() if display else current.aspect
        stretched = abs(current.aspect - native) > 0.02
        self.overlay.show_mode(current.width, current.height, stretched)

    def _on_active_changed(self, profile) -> None:
        if profile is None:
            self.title_bar.status_badge.set_state("No game detected", theme.TEXT_MUTED)
            self.sidebar_status.setText("Desktop values active")
        else:
            self.title_bar.status_badge.set_state(f"{profile.icon}  {profile.name} active",
                                                  theme.SUCCESS)
            self.sidebar_status.setText(f"{profile.name}: {profile.summary()}")
            if self.store.settings.notifications:
                self.flash(f"{profile.name} applied")
        if hasattr(self, "profiles_page"):
            self.profiles_page.reload()
        if hasattr(self, "overlay"):
            self._sync_overlay()

    def _on_profiles_changed(self) -> None:
        self.display_page.update_capabilities()

    def flash(self, message: str) -> None:
        self.title_bar.message.setText(message)
        self._message_timer.start(4000)

    # -- geometry -----------------------------------------------------
    def _restore_geometry(self) -> None:
        saved = self.store.settings.window_geometry
        if saved and len(saved) == 4 and all(v > 0 for v in saved[2:]):
            x, y, width, height = saved
            self.move(x, y)
            self.resize(width, height)
        else:
            screen = self.screen()
            if screen is not None:
                area = screen.availableGeometry()
                self.move(area.center().x() - self.width() // 2,
                          area.center().y() - self.height() // 2)
        if self.store.settings.window_maximized:
            self.showMaximized()

    def _store_geometry(self) -> None:
        settings = self.store.settings
        settings.window_maximized = self.isMaximized()
        if not self.isMaximized():
            geometry = self.normalGeometry()
            settings.window_geometry = [geometry.x(), geometry.y(),
                                        geometry.width(), geometry.height()]
        self.store.save_settings()

    # -- window behaviour ---------------------------------------------
    def quit_app(self) -> None:
        self._force_quit = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._store_geometry()
        if self.store.settings.close_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
            self.flash("")
            return
        self.watch_timer.stop()
        self.enforce_timer.stop()
        self.overlay.hide()
        self.engine.restore_all()
        self.store.save()
        event.accept()
