"""Brightness and contrast straight on the monitor through DDC/CI.

The second path for brightness and contrast: instead of the gamma ramp it
drives the on-screen menu of the monitor. That survives any anti-cheat, but
it is slower and only works when the monitor supports DDC/CI and has it
enabled in its menu.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    dxva2 = ctypes.WinDLL("dxva2", use_last_error=True)
except OSError:  # pragma: no cover - only on exotic systems
    dxva2 = None


class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [("hPhysicalMonitor", wintypes.HANDLE),
                ("szPhysicalMonitorDescription", wintypes.WCHAR * 128)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32)]


if dxva2 is not None:
    LPPM = ctypes.POINTER(PHYSICAL_MONITOR)
    LPDW = ctypes.POINTER(wintypes.DWORD)
    dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, LPDW]
    dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL
    dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, wintypes.DWORD, LPPM]
    dxva2.GetPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL
    dxva2.DestroyPhysicalMonitor.argtypes = [wintypes.HANDLE]
    for _name in ("GetMonitorBrightness", "GetMonitorContrast"):
        _fn = getattr(dxva2, _name)
        _fn.argtypes = [wintypes.HANDLE, LPDW, LPDW, LPDW]
        _fn.restype = wintypes.BOOL
    for _name in ("SetMonitorBrightness", "SetMonitorContrast"):
        _fn = getattr(dxva2, _name)
        _fn.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        _fn.restype = wintypes.BOOL

MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)


@dataclass
class MonitorControl:
    device: str          # \\.\DISPLAY1
    description: str
    brightness: tuple[int, int, int] | None   # min, current, max
    contrast: tuple[int, int, int] | None


def _monitor_handles() -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []

    def callback(hmon, hdc, rect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        device = ""
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            device = info.szDevice
        found.append((hmon, device))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    return found


def _physical(hmon: int):
    count = wintypes.DWORD()
    if not dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(count)):
        return []
    if not count.value:
        return []
    array = (PHYSICAL_MONITOR * count.value)()
    if not dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, count.value, array):
        return []
    return list(array)


def _triplet(fn, handle) -> tuple[int, int, int] | None:
    low, current, high = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
    if fn(handle, ctypes.byref(low), ctypes.byref(current), ctypes.byref(high)):
        return int(low.value), int(current.value), int(high.value)
    return None


def available() -> bool:
    return dxva2 is not None


def probe_status() -> tuple[list[MonitorControl], str]:
    """Monitors that answer over DDC/CI, plus a reason when none of them does."""
    if dxva2 is None:
        return [], "dxva2.dll is missing on this system."
    monitors = _monitor_handles()
    if not monitors:
        return [], "No monitor found."
    controls = probe()
    if controls:
        return controls, ""
    # The driver reports a monitor but hands out no handle: that is what happens
    # when DDC/CI is switched off in the monitor menu, or when the cable path
    # (adapter, KVM, docking station) does not carry the control channel.
    return [], ("The driver hands out no control channel for this monitor. Enable DDC/CI in "
                "the monitor menu, and connect the monitor directly instead of through an "
                "adapter or KVM switch.")


def probe() -> list[MonitorControl]:
    """Every monitor that answers over DDC/CI."""
    if dxva2 is None:
        return []
    results: list[MonitorControl] = []
    for hmon, device in _monitor_handles():
        for physical in _physical(hmon):
            handle = physical.hPhysicalMonitor
            try:
                brightness = _triplet(dxva2.GetMonitorBrightness, handle)
                contrast = _triplet(dxva2.GetMonitorContrast, handle)
            finally:
                dxva2.DestroyPhysicalMonitor(handle)
            if brightness or contrast:
                results.append(MonitorControl(
                    device=device,
                    description=physical.szPhysicalMonitorDescription,
                    brightness=brightness, contrast=contrast))
    return results


def _with_handle(device: str | None, action) -> bool:
    if dxva2 is None:
        return False
    for hmon, dev in _monitor_handles():
        if device and device != "primary" and dev.lower() != device.lower():
            continue
        for physical in _physical(hmon):
            handle = physical.hPhysicalMonitor
            try:
                if action(handle):
                    return True
            finally:
                dxva2.DestroyPhysicalMonitor(handle)
    return False


def set_brightness(device: str | None, percent: int) -> bool:
    percent = max(0, min(100, int(percent)))
    return _with_handle(device, lambda h: bool(dxva2.SetMonitorBrightness(h, percent)))


def set_contrast(device: str | None, percent: int) -> bool:
    percent = max(0, min(100, int(percent)))
    return _with_handle(device, lambda h: bool(dxva2.SetMonitorContrast(h, percent)))


def read_values(device: str | None) -> MonitorControl | None:
    for control in probe():
        if not device or device == "primary" or control.device.lower() == device.lower():
            return control
    return None
