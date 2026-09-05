import tkinter as tk
from tkinter import Toplevel
from tkinter import ttk
from app.ui.components.dialog_text import dialog_label

from app.utils.resource_utils import apply_app_icon
from app.ui.layout_utils import fit_window_to_content

class ControlsWindow:
    """Keyboard shortcuts and mouse controls reference panel..."""

    def __init__(self, parent, translation_service, theme_service, theme_name: str):
        self.parent = parent
        self.t = translation_service
        self.theme_service = theme_service
        self.theme_name = theme_service.normalize_theme_name(theme_name)
        self.colors = self.theme_service.get_color_scheme(self.theme_name)

        self.win = Toplevel(parent)
        self.win.withdraw()
        self.win.title(self.t.get("controls.title", "Controls & Shortcuts"))
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        self.win.bind("<Escape>", lambda _event: self.win.destroy())
        self.win.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.win.bind("<Button-4>", self._on_mousewheel, add="+")
        self.win.bind("<Button-5>", self._on_mousewheel, add="+")
        apply_app_icon(self.win)

        self.win.configure(bg=self.colors["bg"])
        self.theme_service.apply_titlebar(self.win, self.theme_name)
        self._configure_styles()
        self._build_ui()

        self.win.update_idletasks()
        requested_width = self._content_frame.winfo_reqwidth() + 28 + 22 + self._scrollbar.winfo_reqwidth() + 18
        fit_window_to_content(
            self.win,
            self.parent,
            min_width=560,
            min_height=500,
            preferred_width=720,
            preferred_height=700,
            requested_width=requested_width,
            screen_margin_x=80,
            screen_margin_y=100,
        )

        self.win.deiconify()
        self.win.lift()
        self.win.grab_set()
        self.win.focus_set()

    def _configure_styles(self):
        style = ttk.Style(self.win)
        style.configure(
            "ShortcutKey.TLabel",
            background=self.colors["card_bg"],
            foreground=self.colors["fg"],
            font="MewtatorBodyBold",
            padding=(8, 3),
            anchor="center",
        )

    def _label(self, master, **kwargs):
        """Render popup text with explicit colours instead of inherited ttk colours..."""
        style_name = str(kwargs.pop("style", "") or "")
        muted = style_name == "Hint.TLabel"

        if style_name == "ShortcutKey.TLabel":
            kwargs.setdefault("font", "MewtatorBodyBold")
            kwargs.setdefault("background", self.colors["card_bg"])
            kwargs.setdefault("foreground", self.colors["fg"])
            kwargs.setdefault("padx", 8)
            kwargs.setdefault("pady", 3)
            kwargs.setdefault("anchor", "center")
        else:
            kwargs.setdefault("font", "MewtatorBody")

        return dialog_label(master, self.colors, muted=muted, **kwargs)

    def _build_ui(self):
        outer = ttk.Frame(self.win, padding=(28, 24, 22, 20))
        outer.pack(fill="both", expand=True)

        self._label(
            outer,
            text=self.t.get("controls.title", "Controls & Shortcuts"),
            font="MewtatorTitle",
        ).pack(anchor="w")

        self._label(
            outer,
            text=self.t.get(
                "controls.subtitle",
                "A quick reference for Mewtator's keyboard and mouse controls.",
            ),
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(3, 14))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            body,
            highlightthickness=0,
            borderwidth=0,
            background=self.colors["bg"],
        )
        self._scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y", padx=(10, 0))

        content = ttk.Frame(self.canvas)
        self._content_frame = content
        self._content_window = self.canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", self._update_scroll_region, add="+")
        self.canvas.bind("<Configure>", self._resize_content, add="+")

        sections = [
            (
                self.t.get("controls.global", "Global shortcuts"),
                [
                    ("F1", self.t.get("controls.open_controls", "Open this Controls & Shortcuts panel.")),
                    ("F2", self.t.get("controls.open_settings", "Open Settings.")),
                    ("F3", self.t.get("controls.launch_options", "Open Launch Options & Export.")),
                    ("F5", self.t.get("controls.launch_game", "Launch Mewgenics with the current enabled mods.")),
                    ("Ctrl + Q", self.t.get("controls.exit", "Exit Mewtator.")),
                ],
            ),
            (
                self.t.get("controls.mod_list_keyboard", "Mod List: Keyboard"),
                [
                    ("Enter / Space", self.t.get("controls.toggle_selected", "Enable or disable the selected mod.")),
                    ("W", self.t.get("controls.move_up", "Move the selected enabled mod up one position in the load order.")),
                    ("S", self.t.get("controls.move_down", "Move the selected enabled mod down one position in the load order.")),
                    ("Shift + W", self.t.get("controls.move_top", "Move the selected enabled mod to the top of the load order.")),
                    ("Shift + S", self.t.get("controls.move_bottom", "Move the selected enabled mod to the bottom of the load order.")),
                    ("Delete", self.t.get("controls.delete_mod", "Delete the selected mod after confirmation.")),
                ],
            ),
            (
                self.t.get("controls.mouse", "Mod List: Mouse"),
                [
                    (self.t.get("controls.click", "Click"), self.t.get("controls.select_mod", "Select a mod and show its details in the preview panel.")),
                    (self.t.get("controls.checkbox_click", "Checkbox click"), self.t.get("controls.toggle_checkbox", "Enable or disable that mod.")),
                    (self.t.get("controls.double_click", "Double-click"), self.t.get("controls.toggle_row", "Enable or disable the clicked mod row.")),
                    (self.t.get("controls.right_click", "Right-click"), self.t.get("controls.context_menu", "Open the mod context menu.")),
                    (self.t.get("controls.arrow_buttons", "Up / Down buttons"), self.t.get("controls.reorder_buttons", "Move the selected enabled mod one position in the load order.")),
                ],
            ),
        ]

        for section_index, (heading, rows) in enumerate(sections):
            if section_index:
                ttk.Separator(content, orient="horizontal").pack(fill="x", pady=(14, 12))

            self._label(
                content,
                text=heading,
                font="MewtatorHeading",
            ).pack(anchor="w", pady=(0, 6))

            section = ttk.Frame(content)
            section.pack(fill="x")
            section.columnconfigure(0, minsize=170)
            section.columnconfigure(1, weight=1)

            for row_index, (control, description) in enumerate(rows):
                self._label(
                    section,
                    text=control,
                    style="ShortcutKey.TLabel",
                ).grid(row=row_index, column=0, sticky="nw", padx=(0, 16), pady=3)

                self._label(
                    section,
                    text=description,
                    wraplength=420,
                    justify="left",
                ).grid(row=row_index, column=1, sticky="nw", pady=5)

        self._label(
            content,
            text=self.t.get(
                "controls.focus_hint",
                "Mod-list keyboard controls apply while the mod list has keyboard focus. Load-order controls affect enabled mods only.",
            ),
            style="Hint.TLabel",
            wraplength=610,
            justify="left",
        ).pack(anchor="w", pady=(16, 4))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(14, 12))

        button_row = ttk.Frame(outer)
        button_row.pack(fill="x")

        ttk.Button(
            button_row,
            text=self.t.get("messages.close", "Close"),
            command=self.win.destroy,
            cursor="hand2",
        ).pack(side="right")

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_content(self, event):
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _on_mousewheel(self, event):
        if not hasattr(self, "canvas"):
            return

        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            wheel_delta = getattr(event, "delta", 0)
            if not wheel_delta:
                return
            delta = -1 if wheel_delta > 0 else 1

        self.canvas.yview_scroll(delta * 3, "units")
        return "break"

    def _position_dialog(self, width: int, height: int):
        try:
            self.parent.update_idletasks()
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            x = parent_x + max(0, (parent_width - width) // 2)
            y = parent_y + max(0, (parent_height - height) // 2)
        except Exception:
            x = max(0, (self.win.winfo_screenwidth() - width) // 2)
            y = max(0, (self.win.winfo_screenheight() - height) // 2)

        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()
        x = max(0, min(x, max(0, screen_width - width)))
        y = max(0, min(y, max(0, screen_height - height)))
        self.win.geometry(f"{width}x{height}+{x}+{y}")
