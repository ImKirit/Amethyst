"""Creates the images for the project page.

Runs with its own data folder and example profiles so nothing about the real
settings is touched and the images stay reproducible.

    python tools/screenshots.py [target folder]
    python tools/screenshots.py --real-caps    show this machine's real capabilities
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SANDBOX = Path(tempfile.gettempdir()) / "amethyst-shots"
shutil.rmtree(SANDBOX, ignore_errors=True)
SANDBOX.mkdir(parents=True, exist_ok=True)
os.environ["LOCALAPPDATA"] = str(SANDBOX)

from PySide6.QtCore import QPoint, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from amethyst.engine import Engine  # noqa: E402
from amethyst.models import ColorSettings, ResolutionSettings  # noqa: E402
from amethyst.presets import preset_by_name  # noqa: E402
from amethyst.store import Store  # noqa: E402
from amethyst.ui import theme  # noqa: E402
from amethyst.ui.page_profiles import ProcessPicker  # noqa: E402
from amethyst.ui.widgets import app_icon  # noqa: E402
from amethyst.ui.window import MainWindow  # noqa: E402


def demo_profiles(store: Store) -> None:
    """A believable set of profiles for the images."""
    valorant = preset_by_name("Valorant").to_profile()
    valorant.color = ColorSettings(enabled=True, vibrance=78, brightness=6, contrast=54, gamma=1.08)
    valorant.resolution = ResolutionSettings(enabled=True, width=1440, height=1080, refresh=300)

    cs2 = preset_by_name("Counter-Strike 2").to_profile()
    cs2.color = ColorSettings(enabled=True, vibrance=85, contrast=56, gamma=1.10)
    cs2.resolution = ResolutionSettings(enabled=True, width=1280, height=960, refresh=240)

    fortnite = preset_by_name("Fortnite").to_profile()
    fortnite.color = ColorSettings(enabled=True, vibrance=70, gamma=1.05)

    tarkov = preset_by_name("Escape from Tarkov").to_profile()
    tarkov.color = ColorSettings(enabled=True, vibrance=62, brightness=9, gamma=1.22)

    for profile in (valorant, cs2, fortnite, tarkov):
        store.profiles.append(profile)
    store.settings.desktop.color = ColorSettings(enabled=True, vibrance=58, brightness=2,
                                                 contrast=52, gamma=1.04, green=99, blue=102)
    store.save()


def pump(times: int = 4) -> None:
    for _ in range(times):
        QApplication.processEvents()


def shoot(window: MainWindow, page: int, name: str, out: Path) -> None:
    window.nav_group.button(page).setChecked(True)
    window.stack.setCurrentIndex(page)
    pump()
    pixmap = window.grab()
    pixmap.save(str(out / name), "PNG")
    print(f"  {name}  {pixmap.width()}x{pixmap.height()}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(args[0]) if args else ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(app_icon())

    store = Store()
    demo_profiles(store)
    engine = Engine(store)

    # On the capture machine an anti-cheat blocks the gamma ramp. The images
    # show the normal case, otherwise the sliders would be greyed out.
    if "--real-caps" not in sys.argv:
        demo_caps = engine.capabilities
        demo_caps.gamma_ok = True
        demo_caps.gamma_reason = ""
        engine._detect = lambda: demo_caps

    window = MainWindow(engine)
    window.watch_timer.stop()          # never switch profiles while capturing
    window.resize(1100, 780)
    window.show()
    pump()

    print("Images:")
    shoot(window, 0, "main-display.png", out)
    window.profiles_page.reload()
    pump()
    shoot(window, 1, "main-profiles.png", out)
    shoot(window, 2, "main-settings.png", out)

    # template menu behind "New profile"
    window.stack.setCurrentIndex(1)
    window.nav_group.button(1).setChecked(True)
    pump()
    menu, _empty, _actions = window.profiles_page.build_new_menu()
    button = window.profiles_page.new_button
    menu.popup(button.mapToGlobal(QPoint(0, button.height())))
    pump()
    menu.grab().save(str(out / "tour-templates.png"), "PNG")
    print("  tour-templates.png")
    menu.close()

    # picker for running programs
    picker = ProcessPicker(window)
    picker.setStyleSheet(theme.stylesheet())
    picker.resize(430, 470)
    picker.show()
    pump()
    if picker.list.count():
        picker.list.setCurrentRow(min(3, picker.list.count() - 1))
    pump()
    picker.grab().save(str(out / "tour-picker.png"), "PNG")
    print("  tour-picker.png")
    picker.close()

    # how it looks while a game is running
    active = store.profiles[0]
    engine.active = active
    window._on_active_changed(active)
    pump()
    shoot(window, 1, "main-active.png", out)

    # icon file for the header of the project page
    app_icon().pixmap(256, 256).save(str(out / "logo.png"), "PNG")
    print("  logo.png  256x256")

    QTimer.singleShot(0, app.quit)
    app.exec()
    shutil.rmtree(SANDBOX, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
