"""Brightness, contrast, gamma and RGB balance through the GDI gamma ramp.

The ramp sits at the very end of the graphics pipeline, which is why it
also affects games. Windows does not accept it everywhere though: with HDR
enabled, with automatic color management, and whenever a kernel anti-cheat
blocks the access, the calls fail. ``probe`` reports exactly that.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR] * 3 + [ctypes.c_void_p]
gdi32.CreateDCW.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.GetDeviceGammaRamp.restype = wintypes.BOOL
gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL

RampArray = wintypes.WORD * 256 * 3

# Ranges match the NVIDIA control panel
BRIGHTNESS_RANGE = (-50.0, 50.0)
CONTRAST_RANGE = (0.0, 100.0)
GAMMA_RANGE = (0.30, 2.80)
GAIN_RANGE = (50.0, 150.0)

NEUTRAL = dict(brightness=0.0, contrast=50.0, gamma=1.0,
               red=100.0, green=100.0, blue=100.0)


@dataclass
class GammaStatus:
    available: bool
    reason: str = ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_ramp(brightness: float, contrast: float, gamma: float,
               red: float = 100.0, green: float = 100.0, blue: float = 100.0) -> RampArray:
    """Build the gamma ramp from the slider values.

    brightness -50..50, contrast 0..100 (50 neutral), gamma 0.30..2.80,
    channel gains 50..150 percent.
    """
    offset = _clamp(brightness, *BRIGHTNESS_RANGE) / 100.0
    factor = _clamp(contrast, *CONTRAST_RANGE) / 50.0
    gamma = _clamp(gamma, *GAMMA_RANGE)
    gains = [
        _clamp(red, *GAIN_RANGE) / 100.0,
        _clamp(green, *GAIN_RANGE) / 100.0,
        _clamp(blue, *GAIN_RANGE) / 100.0,
    ]

    ramp = RampArray()
    for i in range(256):
        value = i / 255.0
        value = (value - 0.5) * factor + 0.5 + offset
        value = _clamp(value, 0.0, 1.0) ** (1.0 / gamma)
        for channel in range(3):
            scaled = _clamp(value * gains[channel], 0.0, 1.0)
            ramp[channel][i] = int(round(scaled * 65535))
    return ramp


def linear_ramp() -> RampArray:
    return build_ramp(**NEUTRAL)


def _dc(device: str | None):
    return gdi32.CreateDCW("DISPLAY", device, None, None)


def get_ramp(device: str | None = None) -> RampArray | None:
    hdc = _dc(device)
    if not hdc:
        return None
    ramp = RampArray()
    ok = gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(ramp))
    gdi32.DeleteDC(hdc)
    return ramp if ok else None


def set_ramp(ramp: RampArray, device: str | None = None) -> bool:
    hdc = _dc(device)
    if not hdc:
        return False
    ok = bool(gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp)))
    gdi32.DeleteDC(hdc)
    return ok


def apply(device: str | None, brightness: float, contrast: float, gamma: float,
          red: float = 100.0, green: float = 100.0, blue: float = 100.0) -> bool:
    return set_ramp(build_ramp(brightness, contrast, gamma, red, green, blue), device)


def reset(device: str | None = None) -> bool:
    return set_ramp(linear_ramp(), device)


def ramp_to_list(ramp: RampArray) -> list[list[int]]:
    return [[int(ramp[c][i]) for i in range(256)] for c in range(3)]


def ramp_from_list(data: list[list[int]]) -> RampArray:
    ramp = RampArray()
    for c in range(3):
        for i in range(256):
            ramp[c][i] = int(data[c][i]) & 0xFFFF
    return ramp


def gamma_range_unlocked() -> bool:
    """Windows clamps the ramp until GdiIcmGammaRange is set to 256."""
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM")
        value, _ = winreg.QueryValueEx(key, "GdiIcmGammaRange")
        winreg.CloseKey(key)
        return int(value) >= 256
    except OSError:
        return False


def unlock_gamma_range() -> tuple[bool, str]:
    """Unlock the full slider range. Needs administrator rights."""
    try:
        import winreg
    except ImportError:  # pragma: no cover - Windows only
        return False, "winreg is not available"
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM",
            0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "GdiIcmGammaRange", 0, winreg.REG_DWORD, 256)
        winreg.CloseKey(key)
        return True, "Unlocked. The full range applies after the next sign-in."
    except PermissionError:
        return False, "Amethyst has to run as administrator for this."
    except OSError as exc:
        return False, str(exc)


def _anticheat_hint() -> str:
    """Kernel anti-cheats block access to the gamma ramp system wide."""
    from .processes import running_process_names

    known = {
        "vgtray.exe": "Riot Vanguard",
        "vgc.exe": "Riot Vanguard",
        "faceitclient.exe": "FACEIT Anti-cheat",
        "esea.exe": "ESEA Client",
    }
    running = running_process_names()
    found = {label for exe, label in known.items() if exe in running}
    return ", ".join(sorted(found))


def probe(device: str | None = None) -> GammaStatus:
    """Check whether the gamma ramp can be used on this machine."""
    ramp = get_ramp(device)
    if ramp is not None:
        return GammaStatus(True)

    blocker = _anticheat_hint()
    if blocker:
        return GammaStatus(
            False,
            f"{blocker} blocks the gamma ramp system wide. "
            "Digital vibrance and resolution still work.")
    return GammaStatus(
        False,
        "Windows refuses access to the gamma ramp. "
        "This is usually caused by HDR or automatic color management.")
