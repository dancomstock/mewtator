"""Label compatibility helpers for Wine/Proton...

Wine/Proton makes Tk's themed labels shit the bed and draw the wrong background color behind some text...
This fixes that problem!

Wine/Proton and native Linux get a classic Tk label whose background is explicitly matched to its ttk parent/style...
"""

from functools import lru_cache
import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

@lru_cache(maxsize=1)
def running_under_wine() -> bool:
    """Return True when this Windows Python process is hosted by Wine/Proton..."""

    if sys.platform != "win32":
        return False

    # Proton/Wine commonly passes one or more of these through to the Windows process, cheap first check....
    if any(os.environ.get(name) for name in ("WINEPREFIX", "WINELOADERNOEXEC", "STEAM_COMPAT_DATA_PATH", "STEAM_COMPAT_CLIENT_INSTALL_PATH")):
        return True

    # Wine exports wine_get_version from ntdll...
    try:
        ntdll = ctypes.WinDLL("ntdll")
        getattr(ntdll, "wine_get_version")
        return True
    except Exception:
        return False

def _style_name(widget: tk.Misc) -> str:
    try:
        explicit = str(widget.cget("style") or "")
        if explicit:
            return explicit
    except Exception:
        pass

    try:
        return str(widget.winfo_class() or "")
    except Exception:
        return ""

def _lookup_style(master: tk.Misc, style_name: str, option: str) -> Any:
    if not style_name:
        return ""
    try:
        return ttk.Style(master).lookup(style_name, option)
    except Exception:
        return ""

def _parent_background(master: Optional[tk.Misc]) -> str:
    """Resolve the visible background of a Tk/ttk parent hierarchy..."""

    current = master

    while current is not None:
        # Classic Tk widgets expose their actual painted background directly...
        for option in ("background", "bg"):
            try:
                value = current.cget(option)
                if value:
                    return str(value)
            except Exception:
                pass

        # ttk widgets paint through styles. Looking up the parent's style is reliable even on Wine?
        style_name = _style_name(current)
        value = _lookup_style(current, style_name, "background")

        if value:
            return str(value)

        try:
            current = current.master
        except Exception:
            current = None

    # (Matches Mewtator's current theme, final hardcoded fallback)...
    return "#1c1c1c"

def _configured_style_value(style: ttk.Style, style_name: str, option: str) -> Any:
    if not style_name:
        return ""
    try:
        configured = style.configure(style_name) or {}
        value = configured.get(option, "")
        return value if value not in (None, "") else ""
    except Exception:
        return ""

def _rgb(master: tk.Misc, color: str) -> Optional[tuple[float, float, float]]:
    try:
        r, g, b = master.winfo_rgb(color)
        return (r / 65535.0, g / 65535.0, b / 65535.0)
    except Exception:
        return None

def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(value) for value in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _contrast_ratio(master: tk.Misc, foreground: str, background: str) -> float:
    fg_rgb = _rgb(master, foreground)
    bg_rgb = _rgb(master, background)
    if fg_rgb is None or bg_rgb is None:
        return 0.0
    fg_lum = _relative_luminance(fg_rgb)
    bg_lum = _relative_luminance(bg_rgb)
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    return (lighter + 0.05) / (darker + 0.05)

def _readable_foreground(master: tk.Misc, foreground: str, background: str) -> str:
    if foreground and _contrast_ratio(master, foreground, background) >= 3.0:
        return foreground

    bg_rgb = _rgb(master, background)
    if bg_rgb is None:
        return "#e6e6e6"
    return "#1a1a1a" if _relative_luminance(bg_rgb) > 0.45 else "#e6e6e6"

def _padding_values(master: tk.Misc, value: Any) -> tuple[int, int]:
    if value in (None, ""):
        return (0, 0)

    try:
        parts = master.tk.splitlist(value)
    except Exception:
        if isinstance(value, (tuple, list)):
            parts = tuple(value)
        else:
            parts = (value,)

    numbers = []

    for part in parts:
        try:
            numbers.append(int(float(str(part))))
        except Exception:
            numbers.append(0)

    if not numbers:
        return (0, 0)
    if len(numbers) == 1:
        return (numbers[0], numbers[0])
    if len(numbers) == 2:
        return (numbers[0], numbers[1])

    # ttk supports asymmetric four-side padding while tk. Label only supports
    # symmetric x/y padding. Use the larger side so text is never clipped...
    if len(numbers) >= 4:
        return (max(numbers[0], numbers[2]), max(numbers[1], numbers[3]))
    return (max(numbers[0], numbers[2]), numbers[1])

class _CompatLabel(tk.Label):
    def __init__(self, master: tk.Misc, **kwargs: Any):
        style_name = str(kwargs.pop("style", "") or "")
        style = ttk.Style(master)
        effective_style = style_name or "TLabel"

        # Explicit widget options win. Otherwise take typography/foreground
        # from ttk so the label remains visually consistent...
        if "font" not in kwargs:
            font = style.lookup(effective_style, "font")
            if font:
                kwargs["font"] = font

        if "background" not in kwargs and "bg" not in kwargs:
            # Only trust a background that the named style sets directly.
            # Inherited TLabel backgrounds are the value Wine/Proton can render
            # using the host system colour, which is the defect this should avoid...
            style_background = _configured_style_value(
                style, style_name, "background"
            )
            kwargs["background"] = style_background or _parent_background(master)

        background = str(kwargs.get("background", kwargs.get("bg", "")))

        if "foreground" not in kwargs and "fg" not in kwargs:
            foreground = _configured_style_value(
                style, style_name, "foreground"
            ) or style.lookup(effective_style, "foreground")
            # Some Wine ttk builds report the host light-theme foreground for
            # a dark app surface. Never allow that to produce unreadable text...
            kwargs["foreground"] = _readable_foreground(
                master, str(foreground or ""), background
            )

        if "anchor" not in kwargs:
            anchor = style.lookup(effective_style, "anchor")

            if anchor:
                kwargs["anchor"] = anchor

        if "padx" not in kwargs and "pady" not in kwargs:
            padding = style.lookup(effective_style, "padding")
            padx, pady = _padding_values(master, padding)
            kwargs["padx"] = padx
            kwargs["pady"] = pady

        kwargs.setdefault("borderwidth", 0)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("takefocus", 0)

        super().__init__(master, **kwargs)

def needs_compat_label() -> bool:
    """Return True where ttk label backgrounds are unreliable for Mewtator..."""
    return sys.platform.startswith("linux") or running_under_wine()


def Label(master: tk.Misc, **kwargs: Any):
    """Create a normal ttk label unless the platform needs explicit background painting."""
    if needs_compat_label():
        return _CompatLabel(master, **kwargs)
    return ttk.Label(master, **kwargs)