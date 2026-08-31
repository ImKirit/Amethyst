"""List running processes without any extra dependency."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_PATH = 260


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str      # original spelling, e.g. VALORANT-Win64-Shipping.exe

    @property
    def key(self) -> str:
        return self.name.lower()


def list_processes() -> list[ProcessInfo]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == INVALID_HANDLE_VALUE:
        return []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    found: list[ProcessInfo] = []
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return []
        while True:
            found.append(ProcessInfo(int(entry.th32ProcessID), entry.szExeFile))
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return found


def running_process_names() -> set[str]:
    """All running process names, lower case."""
    return {p.key for p in list_processes()}


def user_processes() -> list[ProcessInfo]:
    """Process list for the profile editor, without the obvious system services."""
    skip = {
        "system", "system idle process", "registry", "memory compression", "svchost.exe",
        "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "smss.exe", "winlogon.exe",
        "fontdrvhost.exe", "dwm.exe", "ctfmon.exe", "conhost.exe", "runtimebroker.exe",
        "sihost.exe", "taskhostw.exe", "spoolsv.exe", "searchhost.exe", "audiodg.exe",
        "shellexperiencehost.exe", "startmenuexperiencehost.exe", "dllhost.exe", "wudfhost.exe",
    }
    seen: dict[str, ProcessInfo] = {}
    for proc in list_processes():
        if proc.key in skip or not proc.key.endswith(".exe"):
            continue
        seen.setdefault(proc.key, proc)
    return sorted(seen.values(), key=lambda p: p.name.lower())
