import tkinter as tk
from typing import Callable, Optional

class PointerMenu(tk.Toplevel):
    """Small popup menu whose selectable rows reliably use a hand cursor..."""

    _DEFAULT_FONT = "TkMenuFont"

    def __init__(self, master, cursor: str = "hand2"):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)

        try:
            self.transient(master.winfo_toplevel())
        except tk.TclError:
            pass

        self._cursor = cursor
        self._background = "#2b2b2b"
        self._foreground = "#ffffff"
        self._activebackground = "#3a3a3a"
        self._activeforeground = "#ffffff"
        self._disabledforeground = "#858585"
        self._font = self._DEFAULT_FONT
        self._entries = []
        self._active_index: Optional[int] = None
        self._owner = None

        super().configure(background=self._activebackground)

        self._surface = tk.Frame(
            self,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self._activebackground,
            highlightcolor=self._activebackground,
            background=self._background,
        )

        self._surface.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda _event: self.unpost(), add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")
        self.bind("<Up>", lambda _event: self._move_active(-1), add="+")
        self.bind("<Down>", lambda _event: self._move_active(1), add="+")
        self.bind("<Return>", self._invoke_active, add="+")
        self.bind("<space>", self._invoke_active, add="+")

    def add_command(
        self,
        *,
        label: str,
        command: Optional[Callable] = None,
        accelerator: str = "",
        image=None,
        compound: str = "left",
        state: str = "normal",
        **_kwargs,
    ):
        index = len(self._entries)

        row = tk.Frame(
            self._surface,
            borderwidth=0,
            highlightthickness=0,
            background=self._background,
            cursor=self._cursor if state != "disabled" else "arrow",
            padx=7,
            pady=0,
        )

        row.pack(fill="x")
        row.grid_columnconfigure(1, weight=1)

        icon = tk.Label(
            row,
            borderwidth=0,
            highlightthickness=0,
            background=self._background,
            foreground=self._foreground,
            image=image if image is not None else "",
            cursor=self._cursor if state != "disabled" else "arrow",
        )

        if image is not None:
            icon.grid(row=0, column=0, padx=(1, 7), pady=6, sticky="w")

        text = tk.Label(
            row,
            text=label,
            anchor="w",
            justify="left",
            borderwidth=0,
            highlightthickness=0,
            background=self._background,
            foreground=(
                self._disabledforeground if state == "disabled" else self._foreground
            ),
            font=self._font,
            cursor=self._cursor if state != "disabled" else "arrow",
            padx=0,
            pady=6,
        )

        text.grid(row=0, column=1, sticky="ew")

        accel = tk.Label(
            row,
            text=accelerator,
            anchor="e",
            justify="right",
            borderwidth=0,
            highlightthickness=0,
            background=self._background,
            foreground=(
                self._disabledforeground if state == "disabled" else self._foreground
            ),
            font=self._font,
            cursor=self._cursor if state != "disabled" else "arrow",
            padx=0,
            pady=6,
        )

        if accelerator:
            accel.grid(row=0, column=2, padx=(24, 3), sticky="e")

        entry = {
            "type": "command",
            "row": row,
            "icon": icon,
            "text": text,
            "accelerator": accel,
            "label": label,
            "command": command,
            "accelerator_text": accelerator,
            "image": image,
            "compound": compound,
            "state": state,
        }

        self._entries.append(entry)
        self._bind_entry_events(index)
        self._apply_entry_theme(index)

    def add_separator(self, **_kwargs):
        holder = tk.Frame(
            self._surface,
            borderwidth=0,
            highlightthickness=0,
            background=self._background,
            padx=8,
            pady=4,
        )

        holder.pack(fill="x")

        line = tk.Frame(
            holder,
            height=1,
            borderwidth=0,
            highlightthickness=0,
            background=self._activebackground,
        )

        line.pack(fill="x")
        self._entries.append({"type": "separator", "holder": holder, "line": line})

    def entryconfigure(self, index, **kwargs):
        if index == "end":
            index = len(self._entries) - 1

        index = int(index)

        entry = self._entries[index]

        if entry["type"] != "command":
            return

        if "label" in kwargs:
            entry["label"] = kwargs["label"]
            entry["text"].configure(text=kwargs["label"])

        if "command" in kwargs:
            entry["command"] = kwargs["command"]

        if "accelerator" in kwargs:
            value = kwargs["accelerator"] or ""
            entry["accelerator_text"] = value
            entry["accelerator"].configure(text=value)

            if value:
                entry["accelerator"].grid(row=0, column=2, padx=(24, 3), sticky="e")
            else:
                entry["accelerator"].grid_remove()

        if "image" in kwargs:
            entry["image"] = kwargs["image"]
            entry["icon"].configure(image=kwargs["image"] if kwargs["image"] is not None else "")

            if kwargs["image"] is None:
                entry["icon"].grid_remove()
            else:
                entry["icon"].grid(row=0, column=0, padx=(1, 7), pady=6, sticky="w")

        if "compound" in kwargs:
            entry["compound"] = kwargs["compound"]

        if "state" in kwargs:
            entry["state"] = kwargs["state"]

        self._apply_entry_theme(index)

    entryconfig = entryconfigure

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, str):
            return super().configure(cnf)
        if cnf:
            kwargs = {**cnf, **kwargs}
        if not kwargs:
            return super().configure()

        handled = False

        for key, attr in (
            ("background", "_background"),
            ("foreground", "_foreground"),
            ("activebackground", "_activebackground"),
            ("activeforeground", "_activeforeground"),
            ("disabledforeground", "_disabledforeground"),
            ("font", "_font"),
            ("cursor", "_cursor"),
        ):
            if key in kwargs:
                setattr(self, attr, kwargs.pop(key))
                handled = True

        result = super().configure(**kwargs) if kwargs else None

        if handled:
            self._apply_theme()

        return result

    config = configure

    def post(self, x: int, y: int, owner=None):
        self._active_index = None
        self._owner = owner
        self.update_idletasks()

        width = max(1, self.winfo_reqwidth())
        height = max(1, self.winfo_reqheight())
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, min(int(x), screen_width - width))
        y = max(0, min(int(y), screen_height - height))

        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.lift()

        try:
            self.focus_force()
        except tk.TclError:
            pass

    def unpost(self):
        self._active_index = None

        if self.winfo_exists() and self.state() != "withdrawn":
            self.withdraw()

    def _bind_entry_events(self, index: int):
        entry = self._entries[index]
        widgets = (entry["row"], entry["icon"], entry["text"], entry["accelerator"])

        for widget in widgets:
            widget.bind(
                "<Enter>",
                lambda _event, i=index: self._activate(i),
                add="+",
            )
            widget.bind(
                "<ButtonRelease-1>",
                lambda _event, i=index: self._invoke(i),
                add="+",
            )

    def _activate(self, index: int):
        entry = self._entries[index]

        if entry["type"] != "command" or entry["state"] == "disabled":
            return
        
        previous = self._active_index
        self._active_index = index

        if previous is not None and previous != index:
            self._apply_entry_theme(previous)
        self._apply_entry_theme(index)

    def _apply_entry_theme(self, index: int):
        entry = self._entries[index]

        if entry["type"] != "command":
            return

        disabled = entry["state"] == "disabled"
        active = self._active_index == index and not disabled
        background = self._activebackground if active else self._background

        foreground = (
            self._disabledforeground
            if disabled
            else self._activeforeground if active else self._foreground
        )

        cursor = "arrow" if disabled else self._cursor

        entry["row"].configure(background=background, cursor=cursor)

        for widget in (entry["icon"], entry["text"], entry["accelerator"]):
            widget.configure(
                background=background,
                foreground=foreground,
                font=self._font,
                cursor=cursor,
            )

    def _apply_theme(self):
        super().configure(background=self._activebackground)

        self._surface.configure(
            background=self._background,
            highlightbackground=self._activebackground,
            highlightcolor=self._activebackground,
        )

        for index, entry in enumerate(self._entries):
            if entry["type"] == "command":
                self._apply_entry_theme(index)
            else:
                entry["holder"].configure(background=self._background)
                entry["line"].configure(background=self._activebackground)

    def _invoke(self, index: int):
        entry = self._entries[index]

        if entry["type"] != "command" or entry["state"] == "disabled":
            return
        
        command = entry.get("command")
        self.unpost()

        if command is not None:
            command()

    def _selectable_indices(self):
        return [
            index
            for index, entry in enumerate(self._entries)
            if entry["type"] == "command" and entry["state"] != "disabled"
        ]

    def _move_active(self, direction: int):
        selectable = self._selectable_indices()
        if not selectable:
            return "break"

        if self._active_index not in selectable:
            next_index = selectable[0] if direction > 0 else selectable[-1]
        else:
            position = selectable.index(self._active_index)
            next_index = selectable[(position + direction) % len(selectable)]
        self._activate(next_index)
        return "break"

    def _invoke_active(self, _event=None):
        if self._active_index is not None:
            self._invoke(self._active_index)
        return "break"

    def _on_focus_out(self, _event):
        self.after_idle(self._close_if_focus_left)

    def _close_if_focus_left(self):
        if self.state() == "withdrawn":
            return
        try:
            focused = self.focus_get()
        except tk.TclError:
            focused = None
        if focused is None:
            self.unpost()
            return

        # Clicking the button that owns this popup intentionally moves focus
        # out of the Toplevel before the button's release callback runs. Keep
        # the menu posted for that transition so MenuBarComponent can observe
        # that it is still open and toggle it closed instead of reopening it... - Tim
        if focused is self._owner:
            return

        try:
            if focused.winfo_toplevel() is not self:
                self.unpost()
        except tk.TclError:
            self.unpost()