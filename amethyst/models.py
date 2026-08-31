"""Data model: color values, resolution, profiles and app settings."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from .winapi import gamma
from .winapi.nvapi import VIBRANCE_NEUTRAL


@dataclass
class ColorSettings:
    """Color values of a profile. The scales match the NVIDIA panel."""

    enabled: bool = False
    brightness: float = 0.0       # -50 .. 50
    contrast: float = 50.0        # 0 .. 100, 50 is neutral
    gamma: float = 1.0            # 0.30 .. 2.80
    vibrance: int = VIBRANCE_NEUTRAL   # 0 .. 100, 50 is neutral
    red: float = 100.0            # 50 .. 150
    green: float = 100.0
    blue: float = 100.0

    def is_neutral(self) -> bool:
        return (
            abs(self.brightness) < 0.01
            and abs(self.contrast - 50.0) < 0.01
            and abs(self.gamma - 1.0) < 0.001
            and self.vibrance == VIBRANCE_NEUTRAL
            and all(abs(v - 100.0) < 0.01 for v in (self.red, self.green, self.blue))
        )

    def uses_ramp(self) -> bool:
        """True when brightness, contrast, gamma or a channel differs from neutral."""
        return (
            abs(self.brightness) >= 0.01
            or abs(self.contrast - 50.0) >= 0.01
            or abs(self.gamma - 1.0) >= 0.001
            or any(abs(v - 100.0) >= 0.01 for v in (self.red, self.green, self.blue))
        )

    def clamped(self) -> "ColorSettings":
        def clamp(value, bounds):
            return max(bounds[0], min(bounds[1], value))

        return replace(
            self,
            brightness=clamp(self.brightness, gamma.BRIGHTNESS_RANGE),
            contrast=clamp(self.contrast, gamma.CONTRAST_RANGE),
            gamma=clamp(self.gamma, gamma.GAMMA_RANGE),
            vibrance=int(clamp(self.vibrance, (0, 100))),
            red=clamp(self.red, gamma.GAIN_RANGE),
            green=clamp(self.green, gamma.GAIN_RANGE),
            blue=clamp(self.blue, gamma.GAIN_RANGE),
        )

    @staticmethod
    def neutral() -> "ColorSettings":
        return ColorSettings()


@dataclass
class ResolutionSettings:
    """Resolution of a profile. ``refresh`` 0 means: highest matching rate."""

    enabled: bool = False
    width: int = 0
    height: int = 0
    refresh: int = 0

    def is_set(self) -> bool:
        return self.enabled and self.width > 0 and self.height > 0

    def label(self) -> str:
        if not self.is_set():
            return "unchanged"
        rate = f" @ {self.refresh} Hz" if self.refresh else ""
        return f"{self.width} x {self.height}{rate}"


@dataclass
class Profile:
    """A game profile: colors, resolution and the processes that trigger it."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "New profile"
    icon: str = "🎮"
    enabled: bool = True
    processes: list[str] = field(default_factory=list)
    display: str = "primary"
    color: ColorSettings = field(default_factory=ColorSettings)
    resolution: ResolutionSettings = field(default_factory=ResolutionSettings)
    restore_on_exit: bool = True

    def matches(self, running: set[str]) -> bool:
        if not self.enabled:
            return False
        return any(p.lower() in running for p in self.processes if p.strip())

    def summary(self) -> str:
        parts = []
        if self.color.enabled and not self.color.is_neutral():
            if self.color.vibrance != VIBRANCE_NEUTRAL:
                parts.append(f"Vibrance {self.color.vibrance}")
            if abs(self.color.gamma - 1.0) >= 0.01:
                parts.append(f"Gamma {self.color.gamma:.2f}")
            if abs(self.color.contrast - 50.0) >= 0.5:
                parts.append(f"Contrast {self.color.contrast:.0f}")
            if abs(self.color.brightness) >= 0.5:
                parts.append(f"Brightness {self.color.brightness:+.0f}")
        if self.resolution.is_set():
            parts.append(self.resolution.label())
        return " · ".join(parts) if parts else "no changes"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Profile":
        color = ColorSettings(**{k: v for k, v in (data.get("color") or {}).items()
                                 if k in ColorSettings.__dataclass_fields__})
        resolution = ResolutionSettings(**{k: v for k, v in (data.get("resolution") or {}).items()
                                           if k in ResolutionSettings.__dataclass_fields__})
        return Profile(
            id=data.get("id") or uuid.uuid4().hex[:12],
            name=data.get("name", "Profile"),
            icon=data.get("icon", "🎮"),
            enabled=bool(data.get("enabled", True)),
            processes=[str(p) for p in data.get("processes", [])],
            display=data.get("display", "primary"),
            color=color,
            resolution=resolution,
            restore_on_exit=bool(data.get("restore_on_exit", True)),
        )


@dataclass
class AppSettings:
    """Global settings including the desktop profile."""

    poll_seconds: float = 2.0
    start_minimized: bool = False
    close_to_tray: bool = True
    notifications: bool = True
    apply_desktop_on_start: bool = False
    brightness_source: str = "auto"    # auto | gamma | ddcci
    desktop: Profile = field(default_factory=lambda: Profile(
        id="desktop", name="Desktop", icon="🖥️", processes=[]))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["desktop"] = self.desktop.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppSettings":
        settings = AppSettings()
        for key in ("poll_seconds", "start_minimized", "close_to_tray", "notifications",
                    "apply_desktop_on_start", "brightness_source"):
            if key in data:
                setattr(settings, key, data[key])
        settings.poll_seconds = max(0.5, min(30.0, float(settings.poll_seconds)))
        if isinstance(data.get("desktop"), dict):
            settings.desktop = Profile.from_dict(data["desktop"])
            settings.desktop.id = "desktop"
        return settings
