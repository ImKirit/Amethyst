"""The part that actually puts the values on the monitor.

How it works: on the first change the original state is saved, on disk as
well, so a crash cannot leave the screen tinted. After that exactly one
target applies at a time: the profile of a running game, otherwise the
desktop profile, otherwise the original state.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from .models import ColorSettings, Profile, ResolutionSettings
from .store import Store
from .winapi import ddcci, displays, gamma
from .winapi.nvapi import VIBRANCE_NEUTRAL, nvapi
from .winapi.processes import running_process_names

log = logging.getLogger(__name__)


@dataclass
class Capabilities:
    """What actually works on this machine."""

    gamma_ok: bool = False
    gamma_reason: str = ""
    gamma_range_unlocked: bool = False
    vibrance_ok: bool = False
    vibrance_reason: str = ""
    driver: str = ""
    ddcci_devices: list[str] = field(default_factory=list)

    @property
    def ddcci_ok(self) -> bool:
        return bool(self.ddcci_devices)

    def color_headline(self) -> str:
        if self.gamma_ok and self.vibrance_ok:
            return "Full color control available"
        if self.vibrance_ok:
            return "Digital vibrance available, gamma ramp blocked"
        if self.gamma_ok:
            return "Gamma ramp available, no NVIDIA vibrance"
        return "No color control available"


@dataclass
class DisplayBaseline:
    """Original state of one monitor."""

    device: str
    ramp: list[list[int]] | None = None
    vibrance: int | None = None
    mode: tuple[int, int, int] | None = None

    def to_dict(self) -> dict:
        return {"device": self.device, "ramp": self.ramp,
                "vibrance": self.vibrance, "mode": list(self.mode) if self.mode else None}

    @staticmethod
    def from_dict(data: dict) -> "DisplayBaseline":
        mode = data.get("mode")
        return DisplayBaseline(
            device=data.get("device", "primary"),
            ramp=data.get("ramp"),
            vibrance=data.get("vibrance"),
            mode=tuple(mode) if mode else None,
        )


class Engine:
    """Applies profiles and watches for running games."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.nv = nvapi()
        self.capabilities = self._detect()
        self.active: Profile | None = None
        self.active_since: float = 0.0
        self._baselines: dict[str, DisplayBaseline] = {}
        self._changed_resolution: dict[str, tuple[int, int, int]] = {}
        self.on_change: Callable[[Profile | None], None] | None = None
        self.last_error: str = ""
        self._recover_from_crash()

    # -- Capabilities -------------------------------------------------
    def _detect(self) -> Capabilities:
        status = gamma.probe()
        caps = Capabilities(
            gamma_ok=status.available,
            gamma_reason=status.reason,
            gamma_range_unlocked=gamma.gamma_range_unlocked(),
            vibrance_ok=self.nv.available,
            vibrance_reason=self.nv.reason,
            driver=self.nv.driver,
            ddcci_devices=[c.device for c in ddcci.probe() if c.brightness],
        )
        return caps

    def refresh_capabilities(self) -> Capabilities:
        self.capabilities = self._detect()
        return self.capabilities

    # -- Original state -----------------------------------------------
    def _capture(self, device: str) -> DisplayBaseline:
        if device in self._baselines:
            return self._baselines[device]
        ramp = gamma.get_ramp(device)
        baseline = DisplayBaseline(
            device=device,
            ramp=gamma.ramp_to_list(ramp) if ramp else None,
            vibrance=self.nv.get_vibrance(device) if self.nv.available else None,
            mode=displays.current_mode(device).as_tuple() if displays.current_mode(device) else None,
        )
        self._baselines[device] = baseline
        self._persist_baselines()
        return baseline

    def _persist_baselines(self) -> None:
        self.store.write_baseline({
            "saved_at": time.time(),
            "displays": [b.to_dict() for b in self._baselines.values()],
        })

    def _recover_from_crash(self) -> None:
        """On startup, check whether the last session ended badly."""
        data = self.store.read_baseline()
        entries = data.get("displays") if isinstance(data, dict) else None
        if not entries:
            return
        log.info("Found a backup from the last session, restoring the original state")
        for entry in entries:
            baseline = DisplayBaseline.from_dict(entry)
            self._restore_display(baseline)
        self.store.clear_baseline()

    def _restore_display(self, baseline: DisplayBaseline) -> None:
        if baseline.ramp and self.capabilities.gamma_ok:
            gamma.set_ramp(gamma.ramp_from_list(baseline.ramp), baseline.device)
        elif self.capabilities.gamma_ok:
            gamma.reset(baseline.device)
        if baseline.vibrance is not None and self.nv.available:
            self.nv.set_vibrance(baseline.vibrance, baseline.device)
        if baseline.mode:
            current = displays.current_mode(baseline.device)
            if current and current.as_tuple() != baseline.mode:
                width, height, refresh = baseline.mode
                displays.set_mode(baseline.device, displays.DisplayMode(width, height, refresh))

    # -- Applying -----------------------------------------------------
    def apply_color(self, device: str, color: ColorSettings) -> list[str]:
        """Apply color values right away. Returns notes about what did not work."""
        device = displays.resolve_device(device) or "primary"
        self._capture(device)
        color = color.clamped()
        notes: list[str] = []

        if self.nv.available:
            if not self.nv.set_vibrance(color.vibrance, device):
                notes.append("Digital vibrance could not be set.")
        elif color.vibrance != VIBRANCE_NEUTRAL:
            notes.append("Digital vibrance needs an NVIDIA graphics card.")

        if color.uses_ramp():
            applied = False
            if self.capabilities.gamma_ok:
                applied = gamma.apply(device, color.brightness, color.contrast, color.gamma,
                                      color.red, color.green, color.blue)
                if not applied:
                    self.capabilities = self._detect()
            if not applied:
                if self._apply_via_ddcci(device, color):
                    notes.append("Brightness and contrast were set on the monitor (DDC/CI).")
                else:
                    notes.append(self.capabilities.gamma_reason
                                 or "Brightness, contrast and gamma are blocked.")
        elif self.capabilities.gamma_ok:
            gamma.reset(device)
        return notes

    def _apply_via_ddcci(self, device: str, color: ColorSettings) -> bool:
        """Fallback: set the values through the monitor menu."""
        if self.store.settings.brightness_source == "gamma":
            return False
        if not self.capabilities.ddcci_ok:
            return False
        # map -50..50 onto 0..100 and pass the contrast through
        brightness = int(round(50 + color.brightness))
        ok = ddcci.set_brightness(device, brightness)
        ok = ddcci.set_contrast(device, int(round(color.contrast))) or ok
        return ok

    def apply_resolution(self, device: str, resolution: ResolutionSettings) -> list[str]:
        if not resolution.is_set():
            return []
        device = displays.resolve_device(device) or "primary"
        self._capture(device)
        current = displays.current_mode(device)
        refresh = resolution.refresh
        if not refresh:
            display = next((d for d in displays.list_displays() if d.device == device), None)
            rates = display.refresh_rates(resolution.width, resolution.height) if display else []
            refresh = rates[0] if rates else (current.refresh if current else 60)
        mode = displays.DisplayMode(resolution.width, resolution.height, refresh)
        if current and current.as_tuple() == mode.as_tuple():
            return []
        ok, message = displays.set_mode(device, mode)
        if ok:
            self._changed_resolution[device] = current.as_tuple() if current else (0, 0, 0)
            return []
        self.last_error = message
        return [f"Resolution {mode.label()} rejected: {message}"]

    def apply_profile(self, profile: Profile) -> list[str]:
        device = displays.resolve_device(profile.display) or "primary"
        notes: list[str] = []
        if profile.color.enabled:
            notes += self.apply_color(device, profile.color)
        if profile.resolution.is_set():
            notes += self.apply_resolution(device, profile.resolution)
        return notes

    # -- Switching ----------------------------------------------------
    def activate(self, profile: Profile) -> list[str]:
        notes = self.apply_profile(profile)
        self.active = profile
        self.active_since = time.time()
        if self.on_change:
            self.on_change(profile)
        return notes

    def deactivate(self) -> None:
        """Back to the desktop profile, otherwise to the original state."""
        previous = self.active
        self.active = None
        if previous is not None:
            self._restore_resolution()
        desktop = self.store.settings.desktop
        if desktop.color.enabled or desktop.resolution.is_set():
            self.apply_profile(desktop)
        else:
            self.restore_all(clear=False)
        if self.on_change:
            self.on_change(None)

    def _restore_resolution(self) -> None:
        for device, mode in list(self._changed_resolution.items()):
            if not mode or mode == (0, 0, 0):
                displays.reset_mode(device)
            else:
                width, height, refresh = mode
                displays.set_mode(device, displays.DisplayMode(width, height, refresh))
            self._changed_resolution.pop(device, None)

    def restore_all(self, clear: bool = True) -> None:
        """Reset everything to the state before the first change."""
        self._restore_resolution()
        for baseline in self._baselines.values():
            self._restore_display(baseline)
        if clear:
            self._baselines.clear()
            self.store.clear_baseline()
            self.active = None
            if self.on_change:
                self.on_change(None)

    # -- Watching -----------------------------------------------------
    def poll(self) -> tuple[Profile | None, Profile | None]:
        """Check the running processes and switch when needed.

        Returns (before, after) so the interface can react.
        """
        running = running_process_names()
        match = next((p for p in self.store.profiles if p.matches(running)), None)
        before = self.active

        if match is None:
            if before is not None:
                if before.restore_on_exit:
                    self.deactivate()
                else:
                    self.active = None
                    if self.on_change:
                        self.on_change(None)
            return before, self.active

        if before is None or before.id != match.id:
            self.activate(match)
        return before, self.active

    def status_text(self) -> str:
        if self.active is None:
            return "No game detected"
        minutes = int((time.time() - self.active_since) // 60)
        suffix = f" for {minutes} min" if minutes else ""
        return f"{self.active.name} active{suffix}"
