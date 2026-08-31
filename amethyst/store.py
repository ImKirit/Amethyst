"""Profiles and settings on disk."""

from __future__ import annotations

import json
import logging
from typing import Any

from . import VERSION
from .models import AppSettings, Profile
from .paths import baseline_file, profiles_file, settings_file

log = logging.getLogger(__name__)


def _read_json(path, fallback: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return fallback
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read %s: %s", path, exc)
        return fallback


def _write_json(path, data: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        temp.replace(path)
    except OSError as exc:
        log.error("Could not write %s: %s", path, exc)


class Store:
    """Holds profiles and settings and writes them back immediately."""

    def __init__(self) -> None:
        self.profiles: list[Profile] = []
        self.settings: AppSettings = AppSettings()
        self.load()

    # -- Loading and saving -------------------------------------------
    def load(self) -> None:
        raw = _read_json(profiles_file(), {"version": VERSION, "profiles": []})
        entries = raw.get("profiles", []) if isinstance(raw, dict) else raw
        self.profiles = [Profile.from_dict(item) for item in entries if isinstance(item, dict)]
        self.settings = AppSettings.from_dict(_read_json(settings_file(), {}))

    def save_profiles(self) -> None:
        _write_json(profiles_file(), {
            "version": VERSION,
            "profiles": [p.to_dict() for p in self.profiles],
        })

    def save_settings(self) -> None:
        _write_json(settings_file(), self.settings.to_dict())

    def save(self) -> None:
        self.save_profiles()
        self.save_settings()

    # -- Profile ------------------------------------------------------
    def add(self, profile: Profile) -> Profile:
        self.profiles.append(profile)
        self.save_profiles()
        return profile

    def remove(self, profile_id: str) -> None:
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        self.save_profiles()

    def replace(self, profile: Profile) -> None:
        for index, existing in enumerate(self.profiles):
            if existing.id == profile.id:
                self.profiles[index] = profile
                break
        else:
            self.profiles.append(profile)
        self.save_profiles()

    def by_id(self, profile_id: str) -> Profile | None:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        if profile_id == self.settings.desktop.id:
            return self.settings.desktop
        return None

    def move(self, profile_id: str, offset: int) -> None:
        """Reorder. When several profiles match, the upper one wins."""
        ids = [p.id for p in self.profiles]
        if profile_id not in ids:
            return
        index = ids.index(profile_id)
        target = max(0, min(len(self.profiles) - 1, index + offset))
        if target == index:
            return
        self.profiles.insert(target, self.profiles.pop(index))
        self.save_profiles()

    # -- Backup of the original state ---------------------------------
    def read_baseline(self) -> dict[str, Any]:
        data = _read_json(baseline_file(), {})
        return data if isinstance(data, dict) else {}

    def write_baseline(self, data: dict[str, Any]) -> None:
        _write_json(baseline_file(), data)

    def clear_baseline(self) -> None:
        try:
            baseline_file().unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            log.warning("Could not delete the backup: %s", exc)
