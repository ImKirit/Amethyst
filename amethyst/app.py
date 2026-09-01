"""Program entry point."""

from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME, VERSION
from .engine import Engine
from .paths import log_file
from .store import Store
from . import updater
from .ui import theme
from .ui.tray import Tray
from .ui.widgets import WheelGuard, app_icon
from .ui.window import MainWindow

log = logging.getLogger("amethyst")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file(), encoding="utf-8"), logging.StreamHandler()],
    )


def _set_app_id() -> None:
    """Own identity so Windows groups the taskbar icon correctly."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"imkirit.{APP_NAME}")
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    start_hidden = "--tray" in argv

    _setup_logging()
    _set_app_id()
    log.info("%s %s starting", APP_NAME, VERSION)

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication([a for a in argv if a != "--tray"])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(app_icon())

    guard = WheelGuard(app)
    app.installEventFilter(guard)

    updater.cleanup_old()

    store = Store()
    engine = Engine(store)
    window = MainWindow(engine)

    tray = Tray(window, engine)
    tray.show()

    if store.settings.notifications:
        def announce(profile) -> None:
            if profile is not None:
                tray.notify(APP_NAME, f"{profile.name} applied")

        previous = engine.on_change

        def chained(profile) -> None:
            if previous:
                previous(profile)
            announce(profile)

        engine.on_change = chained

    if store.settings.apply_desktop_on_start:
        desktop = store.settings.desktop
        if desktop.color.enabled or desktop.resolution.is_set():
            engine.apply_profile(desktop)

    if not (start_hidden or store.settings.start_minimized):
        window.show()
    elif not tray.isSystemTrayAvailable():
        window.show()

    if not engine.capabilities.vibrance_ok and not engine.capabilities.gamma_ok:
        QMessageBox.information(
            window if window.isVisible() else None,
            APP_NAME,
            "No color control is reachable on this machine right now.\n\n"
            f"{engine.capabilities.gamma_reason}\n\n"
            "Resolution profiles still work.")

    code = app.exec()
    engine.restore_all()
    store.save()
    log.info("%s stopped", APP_NAME)
    return code
