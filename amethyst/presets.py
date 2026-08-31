"""Ready-made templates for common games.

The process names come from the executables of those games. The color
values are deliberately restrained: visible, but not garish. Every one of
them can be overwritten in the editor.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ColorSettings, Profile, ResolutionSettings


@dataclass(frozen=True)
class GamePreset:
    name: str
    icon: str
    processes: tuple[str, ...]
    vibrance: int = 65
    gamma: float = 1.0
    contrast: float = 50.0
    brightness: float = 0.0
    note: str = ""

    def to_profile(self) -> Profile:
        return Profile(
            name=self.name,
            icon=self.icon,
            processes=list(self.processes),
            color=ColorSettings(
                enabled=True,
                vibrance=self.vibrance,
                gamma=self.gamma,
                contrast=self.contrast,
                brightness=self.brightness,
            ),
            resolution=ResolutionSettings(),
        )


PRESETS: tuple[GamePreset, ...] = (
    GamePreset("Valorant", "🔫", ("VALORANT-Win64-Shipping.exe", "VALORANT.exe"),
               vibrance=75, gamma=1.05,
               note="Vanguard blocks the gamma ramp. Vibrance and resolution still work."),
    GamePreset("Counter-Strike 2", "💣", ("cs2.exe",), vibrance=80, gamma=1.10, contrast=54),
    GamePreset("Fortnite", "🏗️", ("FortniteClient-Win64-Shipping.exe",), vibrance=70, gamma=1.05),
    GamePreset("Apex Legends", "🎯", ("r5apex.exe", "r5apex_dx12.exe"), vibrance=70, gamma=1.08),
    GamePreset("Rainbow Six Siege", "🛡️", ("RainbowSix.exe", "RainbowSix_BE.exe"), vibrance=68),
    GamePreset("Overwatch 2", "🚀", ("Overwatch.exe",), vibrance=65),
    GamePreset("Call of Duty", "🎖️", ("cod.exe", "ModernWarfare.exe", "BlackOpsColdWar.exe"),
               vibrance=70, gamma=1.12, brightness=6),
    GamePreset("Rocket League", "🚗", ("RocketLeague.exe",), vibrance=72),
    GamePreset("League of Legends", "⚔️", ("League of Legends.exe",), vibrance=60),
    GamePreset("Minecraft", "⛏️", ("javaw.exe", "Minecraft.Windows.exe"), vibrance=60, gamma=1.15),
    GamePreset("PUBG", "🪖", ("TslGame.exe",), vibrance=70, contrast=53),
    GamePreset("Rust", "🔧", ("RustClient.exe",), vibrance=68, gamma=1.10),
    GamePreset("Escape from Tarkov", "🎒", ("EscapeFromTarkov.exe",), vibrance=62, gamma=1.20,
               brightness=8),
    GamePreset("Dota 2", "🗡️", ("dota2.exe",), vibrance=62),
    GamePreset("GTA V", "🌴", ("GTA5.exe", "GTA5_Enhanced.exe", "PlayGTAV.exe"), vibrance=65),
)


def preset_by_name(name: str) -> GamePreset | None:
    for preset in PRESETS:
        if preset.name.lower() == name.lower():
            return preset
    return None


def preset_for_process(process: str) -> GamePreset | None:
    process = process.lower()
    for preset in PRESETS:
        if any(p.lower() == process for p in preset.processes):
            return preset
    return None


# Resolutions that are popular for stretched output
STRETCHED_HINTS: tuple[tuple[int, int], ...] = (
    (1440, 1080), (1280, 960), (1024, 768), (1176, 664), (1280, 1024), (1600, 1024),
)
