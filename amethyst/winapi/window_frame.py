"""Give a frameless Qt window the real Windows frame behaviour back.

A window with ``Qt.FramelessWindowHint`` looks the way we want but loses
everything Windows does for a normal window: snapping it against the top edge
to maximize, dragging it to a screen half, dragging the edges to resize, the
shake gesture, the system menu on right click, double click on the title to
maximize.

The trick is not to remove the frame at all. The window keeps its native
style, and ``WM_NCCALCSIZE`` is answered with "the whole window is client
area", so the title bar is simply not drawn. Windows still treats it as a
normal window, so every gesture above keeps working, and we draw our own
title bar into the space.

``WM_NCHITTEST`` then tells Windows which part of our own drawing counts as
the border and which as the title bar.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084

GWL_STYLE = -16
WS_MAXIMIZEBOX = 0x00010000
WS_MINIMIZEBOX = 0x00020000
WS_THICKFRAME = 0x00040000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000

SM_CXSIZEFRAME = 32
SM_CYSIZEFRAME = 33
SM_CXPADDEDBORDER = 92

# Return values of WM_NCHITTEST
HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

RESIZE_BORDER = 6          # how far from the edge a drag resizes, in pixels


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", RECT * 3), ("lppos", ctypes.c_void_p)]


user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.SetForegroundWindow.argtypes = [wintypes.HWND]


def border_width() -> int:
    return (user32.GetSystemMetrics(SM_CXSIZEFRAME)
            + user32.GetSystemMetrics(SM_CXPADDEDBORDER))


def prepare(hwnd: int) -> bool:
    """Keep the native frame but make sure every gesture is allowed."""
    if not hwnd:
        return False
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    wanted = style | WS_THICKFRAME | WS_CAPTION | WS_SYSMENU | WS_MAXIMIZEBOX | WS_MINIMIZEBOX
    if wanted != style:
        user32.SetWindowLongW(hwnd, GWL_STYLE, wanted)
    try:  # a shadow, so the window does not look pasted onto the desktop
        margins = ctypes.c_int * 4
        dwmapi.DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd),
                                            ctypes.byref(margins(1, 1, 1, 1)))
    except (AttributeError, OSError):
        pass
    return True


def handle_nccalcsize(lparam: int, wparam: int, maximized: bool) -> int:
    """Answer WM_NCCALCSIZE: the whole window is client area.

    While maximized the window would otherwise reach past the screen edges by
    the width of the invisible resize border, so that much is taken off.
    """
    if wparam and maximized:
        params = NCCALCSIZE_PARAMS.from_address(lparam)
        border = border_width()
        params.rgrc[0].left += border
        params.rgrc[0].top += border
        params.rgrc[0].right -= border
        params.rgrc[0].bottom -= border
    return 0


def hit_test(x: int, y: int, width: int, height: int, title_height: int,
             in_title: bool, maximized: bool) -> int:
    """Which part of our own drawing is the frame, which is the title bar.

    ``in_title`` says whether the point sits on the title bar background and
    not on one of its buttons, so the buttons stay clickable.
    """
    if not maximized:
        left = x < RESIZE_BORDER
        right = x > width - RESIZE_BORDER
        top = y < RESIZE_BORDER
        bottom = y > height - RESIZE_BORDER
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM

    if y < title_height and in_title:
        return HTCAPTION            # Windows handles dragging, snapping, double click
    return HTCLIENT


def to_foreground(hwnd: int) -> None:
    """Bring the window in front, the way starting a program should."""
    if hwnd:
        user32.SetForegroundWindow(wintypes.HWND(hwnd))
