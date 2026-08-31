"""Where configuration, profiles and logs live."""

from __future__ import annotations

import os
from pathlib import Path

from . import APP_NAME


def data_dir() -> Path:
    """%LOCALAPPDATA%\\Amethyst, falling back to the home directory."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def profiles_file() -> Path:
    return data_dir() / "profiles.json"


def settings_file() -> Path:
    return data_dir() / "settings.json"


def baseline_file() -> Path:
    """State from before the last change, so a crash cannot leave the screen tinted."""
    return data_dir() / "baseline.json"


def log_file() -> Path:
    return data_dir() / "amethyst.log"


def asset(name: str) -> Path:
    return Path(__file__).resolve().parent / "assets" / name
