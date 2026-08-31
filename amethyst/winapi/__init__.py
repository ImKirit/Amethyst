"""Thin ctypes wrappers around the Windows and NVIDIA interfaces.

Every module here wraps exactly one capability and reports through an
``available`` flag or a status message whether that capability actually
works on this machine. The rest of the app only reads those flags.
"""
