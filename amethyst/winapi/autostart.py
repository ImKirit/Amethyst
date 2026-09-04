"""Autostart through the Run key of the signed-in user."""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

from .. import APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command(to_tray: bool = True) -> str:
    """Launch command for the current setup (script or packaged exe).

    ``--tray`` tells Amethyst that Windows started it, which is the only case
    where it may stay hidden.
    """
    suffix = " --tray" if to_tray else ""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"{suffix}'
    launcher = Path(sys.executable)
    pythonw = launcher.with_name("pythonw.exe")
    if pythonw.exists():
        launcher = pythonw
    root = Path(__file__).resolve().parents[2]
    return f'"{launcher}" "{root}\\run.pyw"{suffix}'


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    except OSError:
        return False
    try:
        winreg.QueryValueEx(key, APP_NAME)
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(key)


def set_enabled(enabled: bool, to_tray: bool = True) -> tuple[bool, str]:
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    except OSError as exc:
        return False, str(exc)
    try:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command(to_tray))
            return True, "Autostart enabled."
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        return True, "Autostart disabled."
    except OSError as exc:
        return False, str(exc)
    finally:
        winreg.CloseKey(key)
