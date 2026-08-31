"""Digital vibrance through NVAPI.

NVAPI only exports ``nvapi_QueryInterface``; every other function is looked
up by its fixed id. Vibrance lives in the driver scanout, which is why it
keeps working even when Windows refuses the gamma ramp.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

# Function ids of the NVAPI interface
_FUNCS = {
    "Initialize": 0x0150E828,
    "Unload": 0xD22BDD7E,
    "GetErrorMessage": 0x6C2D048C,
    "GetInterfaceVersionString": 0x01053FA5,
    "EnumNvidiaDisplayHandle": 0x9ABDD40D,
    "GetAssociatedNvidiaDisplayName": 0x22A78B05,
    "GetDVCInfo": 0x4085DE45,
    "SetDVCLevel": 0x172409B4,
    "GetDVCInfoEx": 0x0E45002D,
    "SetDVCLevelEx": 0x4A82C2B1,
}

NVAPI_OK = 0

VIBRANCE_MIN = 0
VIBRANCE_MAX = 100
VIBRANCE_NEUTRAL = 50


class _DVCInfo(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("currentLevel", ctypes.c_int32),
                ("minLevel", ctypes.c_int32), ("maxLevel", ctypes.c_int32)]


class _DVCInfoEx(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("currentLevel", ctypes.c_int32),
                ("minLevel", ctypes.c_int32), ("maxLevel", ctypes.c_int32),
                ("defaultLevel", ctypes.c_int32)]


def _version(struct_type) -> int:
    return ctypes.sizeof(struct_type) | (1 << 16)


@dataclass
class VibranceDisplay:
    handle: int
    device: str          # \\.\DISPLAY1
    minimum: int
    maximum: int
    default: int


class NvApi:
    """Small NVAPI wrapper. Without an NVIDIA driver ``available`` stays False."""

    def __init__(self) -> None:
        self.available = False
        self.reason = ""
        self.driver = ""
        self._displays: list[VibranceDisplay] = []
        self._extended = False
        self._fn: dict[str, int] = {}
        self._load()

    # -- Setup --------------------------------------------------------
    def _load(self) -> None:
        try:
            self._dll = ctypes.WinDLL("nvapi64.dll")
        except OSError:
            self.reason = "nvapi64.dll was not found, so there is no NVIDIA card in use."
            return

        query = self._dll.nvapi_QueryInterface
        query.restype = ctypes.c_void_p
        query.argtypes = [ctypes.c_uint32]
        self._fn = {name: query(fid) or 0 for name, fid in _FUNCS.items()}

        if not self._fn.get("Initialize"):
            self.reason = "NVAPI does not expose an initialization function."
            return
        if ctypes.CFUNCTYPE(ctypes.c_int)(self._fn["Initialize"])() != NVAPI_OK:
            self.reason = "NVAPI could not be initialized."
            return

        self._extended = bool(self._fn.get("SetDVCLevelEx") and self._fn.get("GetDVCInfoEx"))
        self._read_version()
        self._enumerate()
        if not self._displays:
            self.reason = "No NVIDIA display found."
            return
        self.available = True

    def _read_version(self) -> None:
        ptr = self._fn.get("GetInterfaceVersionString")
        if not ptr:
            return
        buf = ctypes.create_string_buffer(64)
        if ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p)(ptr)(buf) == NVAPI_OK:
            self.driver = buf.value.decode("ascii", "replace")

    def _enumerate(self) -> None:
        enum = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint32,
                                ctypes.POINTER(ctypes.c_void_p))(self._fn["EnumNvidiaDisplayHandle"])
        get_name = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_char_p)(self._fn["GetAssociatedNvidiaDisplayName"])
        index = 0
        while True:
            handle = ctypes.c_void_p()
            if enum(index, ctypes.byref(handle)) != NVAPI_OK:
                break
            name = ctypes.create_string_buffer(64)
            get_name(handle, name)
            info = self._info(handle.value)
            if info is not None:
                minimum, maximum, default = info
                self._displays.append(VibranceDisplay(
                    handle=handle.value,
                    device=name.value.decode("ascii", "replace"),
                    minimum=minimum, maximum=maximum, default=default))
            index += 1

    # -- Queries ------------------------------------------------------
    def _info(self, handle: int) -> tuple[int, int, int] | None:
        if self._extended:
            info = _DVCInfoEx()
            info.version = _version(_DVCInfoEx)
            fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                                  ctypes.POINTER(_DVCInfoEx))(self._fn["GetDVCInfoEx"])
            if fn(ctypes.c_void_p(handle), 0, ctypes.byref(info)) == NVAPI_OK:
                return info.minLevel, info.maxLevel, info.defaultLevel
        info = _DVCInfo()
        info.version = _version(_DVCInfo)
        ptr = self._fn.get("GetDVCInfo")
        if not ptr:
            return None
        fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.POINTER(_DVCInfo))(ptr)
        if fn(ctypes.c_void_p(handle), 0, ctypes.byref(info)) == NVAPI_OK:
            middle = (info.minLevel + info.maxLevel) // 2
            return info.minLevel, info.maxLevel, middle
        return None

    def displays(self) -> list[VibranceDisplay]:
        return list(self._displays)

    def _find(self, device: str | None) -> VibranceDisplay | None:
        if not self._displays:
            return None
        if not device or device == "primary":
            return self._displays[0]
        for display in self._displays:
            if display.device.lower() == device.lower():
                return display
        return self._displays[0]

    def get_vibrance(self, device: str | None = None) -> int | None:
        """Current value on the driver scale (0..100, 50 is neutral)."""
        target = self._find(device)
        if target is None:
            return None
        if self._extended:
            info = _DVCInfoEx()
            info.version = _version(_DVCInfoEx)
            fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                                  ctypes.POINTER(_DVCInfoEx))(self._fn["GetDVCInfoEx"])
            if fn(ctypes.c_void_p(target.handle), 0, ctypes.byref(info)) == NVAPI_OK:
                return self._to_scale(target, info.currentLevel)
        info = _DVCInfo()
        info.version = _version(_DVCInfo)
        fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.POINTER(_DVCInfo))(self._fn["GetDVCInfo"])
        if fn(ctypes.c_void_p(target.handle), 0, ctypes.byref(info)) == NVAPI_OK:
            return self._to_scale(target, info.currentLevel)
        return None

    def set_vibrance(self, level: int, device: str | None = None) -> bool:
        """Set a value on the 0..100 scale (50 equals the default Windows saturation)."""
        target = self._find(device)
        if target is None:
            return False
        raw = self._from_scale(target, level)
        if self._extended:
            # The extended call takes the filled struct, not a plain number.
            info = _DVCInfoEx()
            info.version = _version(_DVCInfoEx)
            info.currentLevel = raw
            info.minLevel = target.minimum
            info.maxLevel = target.maximum
            info.defaultLevel = target.default
            fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
                                  ctypes.POINTER(_DVCInfoEx))(self._fn["SetDVCLevelEx"])
            if fn(ctypes.c_void_p(target.handle), 0, ctypes.byref(info)) == NVAPI_OK:
                return True
        ptr = self._fn.get("SetDVCLevel")
        if not ptr:
            return False
        fn = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32)(ptr)
        return fn(ctypes.c_void_p(target.handle), 0, ctypes.c_uint32(raw)) == NVAPI_OK

    def reset(self, device: str | None = None) -> bool:
        target = self._find(device)
        if target is None:
            return False
        return self.set_vibrance(self._to_scale(target, target.default), device)

    # -- Scales -------------------------------------------------------
    @staticmethod
    def _to_scale(display: VibranceDisplay, raw: int) -> int:
        """Map a driver value onto 0..100."""
        span = display.maximum - display.minimum
        if span <= 0:
            return VIBRANCE_NEUTRAL
        if (display.minimum, display.maximum) == (VIBRANCE_MIN, VIBRANCE_MAX):
            return int(raw)
        return round((raw - display.minimum) * 100 / span)

    @staticmethod
    def _from_scale(display: VibranceDisplay, level: int) -> int:
        level = max(VIBRANCE_MIN, min(VIBRANCE_MAX, int(level)))
        if (display.minimum, display.maximum) == (VIBRANCE_MIN, VIBRANCE_MAX):
            return level
        span = display.maximum - display.minimum
        return display.minimum + round(level * span / 100)


_instance: NvApi | None = None


def nvapi() -> NvApi:
    """Shared NVAPI instance."""
    global _instance
    if _instance is None:
        _instance = NvApi()
    return _instance
