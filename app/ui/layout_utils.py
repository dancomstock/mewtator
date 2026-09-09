"""Small Tk layout helpers for localization-safe sizing stuff...
"""

from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Iterable, Optional, Tuple


def _screen_limit(total: int, margin: int) -> int:
    """Return a usable screen dimension without ever producing <= 0."""
    return max(1, total - max(0, margin))


def center_window(
    window: tk.Misc,
    parent: Optional[tk.Misc],
    width: int,
    height: int,
) -> Tuple[int, int]:
    """Center *window* over *parent* when possible, otherwise on screen."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    parent_visible = False
    if parent is not None:
        try:
            parent.update_idletasks()
            parent_visible = bool(parent.winfo_viewable())
        except (tk.TclError, AttributeError):
            parent_visible = False

    if parent_visible:
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        except (tk.TclError, AttributeError):
            parent_visible = False

    if not parent_visible:
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

    x = max(0, min(x, max(0, screen_width - width)))
    y = max(0, min(y, max(0, screen_height - height)))
    window.geometry(f"{width}x{height}+{x}+{y}")
    return width, height


def fit_window_to_content(
    window: tk.Misc,
    parent: Optional[tk.Misc] = None,
    *,
    min_width: int = 0,
    min_height: int = 0,
    preferred_width: int = 0,
    preferred_height: int = 0,
    requested_width: Optional[int] = None,
    requested_height: Optional[int] = None,
    screen_margin_x: int = 40,
    screen_margin_y: int = 80,
    set_minsize: bool = False,
) -> Tuple[int, int]:
    """Fit its actual localized content and keep it on screen...
    """
    window.update_idletasks()

    natural_width = max(1, window.winfo_reqwidth())
    natural_height = max(1, window.winfo_reqheight())

    if requested_width is not None:
        natural_width = max(natural_width, int(requested_width))
    if requested_height is not None:
        natural_height = max(natural_height, int(requested_height))

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    max_width = _screen_limit(screen_width, screen_margin_x)
    max_height = _screen_limit(screen_height, screen_margin_y)

    width = min(max_width, max(min_width, preferred_width, natural_width))
    height = min(max_height, max(min_height, preferred_height, natural_height))

    if set_minsize:
        # Never set a minimum larger than the usable desktop... - Tim
        window.minsize(min(max_width, max(1, min_width)), min(max_height, max(1, min_height)))

    return center_window(window, parent, width, height)


def fit_combobox_to_values(
    combobox: ttk.Combobox,
    values: Iterable[str],
    *,
    min_chars: int = 12,
    extra_chars: int = 3,
) -> int:
    """Set ttk Combobox character width from the widest value..."""
    values = [str(value) for value in values]
    if not values:
        combobox.configure(width=min_chars)
        return min_chars

    try:
        style = ttk.Style(combobox)
        style_name = str(combobox.cget("style") or "TCombobox")
        font_spec = style.lookup(style_name, "font") or combobox.cget("font") or "TkTextFont"
        try:
            font = tkfont.nametofont(str(font_spec), root=combobox)
        except tk.TclError:
            font = tkfont.Font(root=combobox, font=font_spec)

        widest_px = max(font.measure(value) for value in values)
        unit_px = max(1, font.measure("0"))
        width_chars = math.ceil(widest_px / unit_px) + extra_chars
    except (tk.TclError, TypeError, ValueError):
        width_chars = max(len(value) for value in values) + extra_chars

    width_chars = max(min_chars, width_chars)
    combobox.configure(width=width_chars)
    return width_chars
