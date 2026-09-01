"""Asking about, downloading and installing an update, with a progress dialog."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from .. import APP_NAME, VERSION
from .. import updater


class UpdateFlow(QObject):
    """Runs the network parts off the interface thread."""

    found = Signal(object)          # updater.Release
    nothing = Signal(str)           # message for the status line
    progress = Signal(int)          # percent
    failed = Signal(str)
    ready = Signal()

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self._dialog: QProgressDialog | None = None
        self.found.connect(self._offer)
        self.progress.connect(self._on_progress)
        self.failed.connect(self._on_failed)
        self.ready.connect(self._on_ready)

    # -- checking -----------------------------------------------------
    def check(self, quiet: bool = True) -> None:
        """Ask GitHub for the latest release. Runs in the background."""

        def work() -> None:
            release = updater.check()
            if release is not None:
                self.found.emit(release)
            elif not quiet:
                self.nothing.emit(f"{APP_NAME} {VERSION} is the latest version")

        threading.Thread(target=work, daemon=True).start()

    # -- offering -----------------------------------------------------
    def _offer(self, release) -> None:
        notes = release.notes.strip()
        if len(notes) > 700:
            notes = notes[:700].rsplit("\n", 1)[0] + "\n..."

        box = QMessageBox(self.window)
        box.setWindowTitle(f"{APP_NAME} {release.version} is available")
        box.setText(f"You are running {VERSION}, version {release.version} is out.")
        box.setInformativeText(
            f"{notes}\n\nDownload size: {release.size_mb:.1f} MB"
            if notes else f"Download size: {release.size_mb:.1f} MB")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Update now")
        box.button(QMessageBox.No).setText("Later")
        box.setDefaultButton(QMessageBox.Yes)
        box.setStyleSheet(self.window.styleSheet())
        if box.exec() != QMessageBox.Yes:
            return

        if updater.running_exe() is None:
            QMessageBox.information(
                self.window, APP_NAME,
                "Amethyst is running from source, so it cannot replace itself.\n\n"
                f"Get the new version from {release.page}")
            return

        self._dialog = QProgressDialog(f"Downloading {APP_NAME} {release.version}",
                                       "Cancel", 0, 100, self.window)
        self._dialog.setWindowTitle(APP_NAME)
        self._dialog.setWindowModality(Qt.WindowModal)
        self._dialog.setAutoClose(False)
        self._dialog.setStyleSheet(self.window.styleSheet())
        self._dialog.show()

        def work() -> None:
            try:
                path = updater.download(release, lambda f: self.progress.emit(int(f * 100)))
            except Exception as exc:                      # noqa: BLE001 - report anything
                self.failed.emit(str(exc))
                return
            if updater.install_and_restart(path):
                self.ready.emit()
            else:
                self.failed.emit("The new version could not be installed.")

        threading.Thread(target=work, daemon=True).start()

    # -- reactions ----------------------------------------------------
    def _on_progress(self, percent: int) -> None:
        if self._dialog is not None:
            self._dialog.setValue(percent)

    def _on_failed(self, message: str) -> None:
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None
        QMessageBox.warning(self.window, APP_NAME, f"Update failed.\n\n{message}")

    def _on_ready(self) -> None:
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None
        self.window.quit_app()
        QApplication.quit()
