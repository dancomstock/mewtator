"""Reliable text widgets for Mewtator's dialogs...
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Mapping

def dialog_frame(master: tk.Misc, colors: Mapping[str, str], **kwargs: Any) -> tk.Frame:
    """Create a flat dialog frame with an explicit application background..."""
    kwargs.setdefault("background", colors["bg"])
    kwargs.setdefault("borderwidth", 0)
    kwargs.setdefault("highlightthickness", 0)
    return tk.Frame(master, **kwargs)

def dialog_label(
    master: tk.Misc,
    colors: Mapping[str, str],
    *,
    muted: bool = False,
    foreground: str | None = None,
    **kwargs: Any,
) -> tk.Label:
    """Create dialog text with explicit foreground/background colours...

    ``foreground`` wins over the standard/muted palette choice so warning and
    link text can opt into their own colour without giving up the reliable
    background painting.
    """
    kwargs.setdefault("background", colors["bg"])
    kwargs.setdefault(
        "foreground",
        foreground or (colors.get("muted_fg", colors["fg"]) if muted else colors["fg"]),
    )
    kwargs.setdefault("borderwidth", 0)
    kwargs.setdefault("highlightthickness", 0)
    kwargs.setdefault("relief", "flat")
    return tk.Label(master, **kwargs)