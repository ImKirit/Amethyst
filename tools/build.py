"""Builds Amethyst.exe with PyInstaller.

    python tools/build.py            single file in dist/
    python tools/build.py --folder   folder with a launcher (starts faster)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from amethyst import APP_NAME, VERSION  # noqa: E402

ICON = ROOT / "amethyst" / "assets" / "amethyst.ico"


def ensure_icon() -> None:
    """Write the app icon as .ico when it is missing."""
    if ICON.exists():
        return
    from PySide6.QtGui import QGuiApplication  # noqa: PLC0415
    from amethyst.ui.widgets import app_icon  # noqa: PLC0415

    app = QGuiApplication.instance() or QGuiApplication([])
    icon = app_icon()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [icon.pixmap(size, size).toImage() for size in sizes]
    biggest = images[-1]
    ICON.parent.mkdir(parents=True, exist_ok=True)
    # Qt writes the ICO from the largest image; Windows scales it down itself.
    biggest.save(str(ICON), "ICO")
    del app


def main() -> int:
    ensure_icon()
    one_file = "--folder" not in sys.argv

    for folder in ("build", "dist"):
        shutil.rmtree(ROOT / folder, ignore_errors=True)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--icon", str(ICON),
        "--add-data", f"{ROOT / 'amethyst' / 'assets'}{';'}amethyst/assets",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--onefile" if one_file else "--onedir",
        str(ROOT / "run.pyw"),
    ]
    print(f"Building {APP_NAME} {VERSION} ({'single file' if one_file else 'folder'})")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode == 0:
        target = ROOT / "dist" / (f"{APP_NAME}.exe" if one_file else APP_NAME)
        print(f"Done: {target}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
