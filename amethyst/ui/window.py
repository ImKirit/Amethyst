"""Main window: own title bar, navigation on the left, pages on the right."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton, QSizeGrip,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, VERSION
from ..engine import Engine
from . import theme
from .page_display import DisplayPage
from .page_profiles import ProfilesPage
from .overlay import ResolutionOverlay
from .page_settings import SettingsPage
from .updates import UpdateFlow
from .widgets import Badge, IconButton, app_icon, divider, label, wordmark_font


class TitleBar(QWidget):
    """Slim bar for dragging, minimizing and closing."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self._window = window
        self._press: QPoint | None = None
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 12, 8)
        layout.setSpacing(10)

        self.status_badge = Badge("No game detected", theme.TEXT_MUTED)
        layout.addWidget(self.status_badge)
        layout.addStretch(1)

        self.message = QLabel("")
        self.message.setObjectName("faint")
        layout.addWidget(self.message)

        minimize = IconButton("–", "Minimize")
        minimize.clicked.connect(window.showMinimized)
        close = IconButton("✕", "Close")
        close.setObjectName("closeButton")
        close.clicked.connect(window.close)
        layout.addWidget(minimize)
        layout.addWidget(close)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            self._press = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._press is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._press = None


class MainWindow(QWidget):
    """The frame around the three pages."""

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self.engine = engine
        self.store = engine.store
        self._force_quit = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMinimumSize(960, 700)
        self.resize(1060, 760)

        root = QWidget(self)
        root.setObjectName("root")
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.addWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
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
            holder_layout.setContentsMargins(28, 20, 28, 22)
            holder_layout.addWidget(page)
            self.stack.addWidget(holder)
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 4, 4)
        grip_row.addStretch(1)
        grip_row.addWidget(QSizeGrip(self), 0, Qt.AlignBottom | Qt.AlignRight)
        outer.addLayout(grip_row)

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

        # The resolution is checked more often than the process list: a game
        # switching to full screen resets it within a moment, and waiting two
        # seconds for that is very visible.
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

    # -- Layout -------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(212)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 18)
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

    # -- Runtime ------------------------------------------------------
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

    # -- Window behaviour ---------------------------------------------
    def quit_app(self) -> None:
        self._force_quit = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
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
