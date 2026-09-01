"""Enumerate monitors and set resolution, refresh rate and color depth."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field

user32 = ctypes.WinDLL("user32", use_last_error=True)

# EnumDisplayDevices StateFlags
ATTACHED_TO_DESKTOP = 0x00000001
PRIMARY_DEVICE = 0x00000004

# EnumDisplaySettingsEx
ENUM_CURRENT_SETTINGS = -1
ENUM_REGISTRY_SETTINGS = -2

# DEVMODE dmFields
DM_BITSPERPEL = 0x00040000
DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000
DM_DISPLAYFREQUENCY = 0x00400000

# ChangeDisplaySettingsEx flags
CDS_UPDATEREGISTRY = 0x00000001
CDS_TEST = 0x00000002
CDS_FULLSCREEN = 0x00000004  # temporary: does not survive a reboot
CDS_GLOBAL = 0x00000008
CDS_RESET = 0x40000000

DISP_CHANGE_SUCCESSFUL = 0
CHANGE_ERRORS = {
    0: "Applied",
    1: "Restart required",
    -1: "Mode rejected by the driver",
    -2: "The graphics driver does not support this mode",
    -3: "Writing to the registry failed",
    -4: "Unknown error",
    -5: "Invalid mode",
    -6: "Invalid parameters",
}


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", ctypes.c_long),
        ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


user32.EnumDisplayDevicesW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DISPLAY_DEVICEW), wintypes.DWORD]
user32.EnumDisplayDevicesW.restype = wintypes.BOOL
user32.EnumDisplaySettingsExW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW), wintypes.DWORD]
user32.EnumDisplaySettingsExW.restype = wintypes.BOOL
user32.ChangeDisplaySettingsExW.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(DEVMODEW), wintypes.HWND, wintypes.DWORD, wintypes.LPVOID]
user32.ChangeDisplaySettingsExW.restype = ctypes.c_long


@dataclass(frozen=True)
class DisplayMode:
    width: int
    height: int
    refresh: int

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 0.0

    def label(self) -> str:
        return f"{self.width} x {self.height} @ {self.refresh} Hz"

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.width, self.height, self.refresh)

    def matches(self, other: "DisplayMode | None", tolerance: int = 2) -> bool:
        """Same mode, allowing for rounded refresh rates.

        Drivers report 59 Hz for a mode that was requested as 60, and 143 for
        144. Without the tolerance, anything watching the mode would think it
        was changed and would set it again in a loop.
        """
        if other is None:
            return False
        if (self.width, self.height) != (other.width, other.height):
            return False
        if not self.refresh or not other.refresh:
            return True
        return abs(self.refresh - other.refresh) <= tolerance


@dataclass
class Display:
    device: str          # e.g. \\.\DISPLAY1
    name: str            # adapter description
    monitor: str         # monitor description, when available
    primary: bool
    current: DisplayMode
    modes: list[DisplayMode] = field(default_factory=list)

    @property
    def label(self) -> str:
        num = self.device.rsplit("DISPLAY", 1)[-1]
        tag = " (main)" if self.primary else ""
        return f"Display {num}{tag} - {self.monitor or self.name}"

    def native_aspect(self) -> float:
        """The largest reported resolution defines the native aspect ratio."""
        if not self.modes:
            return self.current.aspect
        widest = max(self.modes, key=lambda m: (m.width * m.height))
        return widest.aspect

    def resolutions(self) -> list[tuple[int, int]]:
        seen = {(m.width, m.height) for m in self.modes}
        return sorted(seen, key=lambda r: (-r[0], -r[1]))

    def refresh_rates(self, width: int, height: int) -> list[int]:
        rates = {m.refresh for m in self.modes if m.width == width and m.height == height}
        return sorted(rates, reverse=True)


def _mode_from_devmode(dm: DEVMODEW) -> DisplayMode:
    return DisplayMode(int(dm.dmPelsWidth), int(dm.dmPelsHeight), int(dm.dmDisplayFrequency))


def current_mode(device: str) -> DisplayMode | None:
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    if not user32.EnumDisplaySettingsExW(device, ENUM_CURRENT_SETTINGS, ctypes.byref(dm), 0):
        return None
    return _mode_from_devmode(dm)


def _all_modes(device: str) -> list[DisplayMode]:
    modes: set[DisplayMode] = set()
    index = 0
    while True:
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if not user32.EnumDisplaySettingsExW(device, index, ctypes.byref(dm), 0):
            break
        index += 1
        if dm.dmBitsPerPel != 32 or dm.dmDisplayFrequency <= 1:
            continue
        modes.add(_mode_from_devmode(dm))
    return sorted(modes, key=lambda m: (-m.width, -m.height, -m.refresh))


def _monitor_name(device: str) -> str:
    mon = DISPLAY_DEVICEW()
    mon.cb = ctypes.sizeof(DISPLAY_DEVICEW)
    if user32.EnumDisplayDevicesW(device, 0, ctypes.byref(mon), 0):
        return mon.DeviceString
    return ""


def list_displays() -> list[Display]:
    """All active monitors together with their modes."""
    displays: list[Display] = []
    index = 0
    while True:
        dev = DISPLAY_DEVICEW()
        dev.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(dev), 0):
            break
        index += 1
        if not dev.StateFlags & ATTACHED_TO_DESKTOP:
            continue
        cur = current_mode(dev.DeviceName)
        if cur is None:
            continue
        displays.append(
            Display(
                device=dev.DeviceName,
                name=dev.DeviceString,
                monitor=_monitor_name(dev.DeviceName),
                primary=bool(dev.StateFlags & PRIMARY_DEVICE),
                current=cur,
                modes=_all_modes(dev.DeviceName),
            )
        )
    displays.sort(key=lambda d: (not d.primary, d.device))
    return displays


def primary_display() -> Display | None:
    for display in list_displays():
        if display.primary:
            return display
    displays = list_displays()
    return displays[0] if displays else None


def resolve_device(device: str | None) -> str | None:
    """Map "primary" and empty values onto a real device name."""
    if device and device != "primary":
        return device
    display = primary_display()
    return display.device if display else None


def _devmode_for(mode: DisplayMode) -> DEVMODEW:
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL
    dm.dmPelsWidth = mode.width
    dm.dmPelsHeight = mode.height
    dm.dmBitsPerPel = 32
    if mode.refresh:
        dm.dmFields |= DM_DISPLAYFREQUENCY
        dm.dmDisplayFrequency = mode.refresh
    return dm


def test_mode(device: str, mode: DisplayMode) -> bool:
    """Check whether a mode could be applied, without applying it."""
    dm = _devmode_for(mode)
    return user32.ChangeDisplaySettingsExW(device, ctypes.byref(dm), None, CDS_TEST, None) == DISP_CHANGE_SUCCESSFUL


def set_mode(device: str, mode: DisplayMode, permanent: bool = False) -> tuple[bool, str]:
    """Apply a display mode.

    ``permanent=False`` keeps the mode out of the registry, so after a crash
    or a reboot the desktop is back to normal.
    """
    dm = _devmode_for(mode)
    flags = CDS_UPDATEREGISTRY if permanent else CDS_FULLSCREEN
    result = user32.ChangeDisplaySettingsExW(device, ctypes.byref(dm), None, flags, None)
    if result != DISP_CHANGE_SUCCESSFUL and not permanent:
        # Some drivers dislike the temporary path, so fall back to the regular one.
        result = user32.ChangeDisplaySettingsExW(
            device, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
    ok = result == DISP_CHANGE_SUCCESSFUL
    return ok, CHANGE_ERRORS.get(result, f"Fehlercode {result}")


def reset_mode(device: str) -> None:
    """Return to the mode stored in the registry."""
    user32.ChangeDisplaySettingsExW(device, None, None, 0, None)
