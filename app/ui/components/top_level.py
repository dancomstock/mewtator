"""Tk Toplevel override.

Tk normally sets the WM_CLASS of Toplevel windows to "Toplevel" (even if the main window had an explicit className override
with tk.Tk(className=...)).

When Mewtator's main window is not shown, a Wayland-based window manager does not know which app owns generically named
"Toplevel" windows.

Mewtator can show its language select and settings menu without the main window. Without setting WM_CLASS on those toplevels,
those windows would not identify correctly.

Hence, we set WM_CLASS on all our Toplevel instances to avoid this problem.
"""

import tkinter as tk

class Toplevel(tk.Toplevel):
    def __init__(self, master=None, cnf={}, **kw):
        kw.setdefault("class_", "Mewtator")
        super().__init__(master, cnf, **kw)
