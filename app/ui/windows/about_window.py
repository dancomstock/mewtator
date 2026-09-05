from tkinter import Toplevel
from tkinter import ttk
from app.ui.components.dialog_text import dialog_frame, dialog_label
from app.utils.resource_utils import apply_app_icon
from app.ui.layout_utils import fit_window_to_content
from app.version import APP_VERSION_DISPLAY

class AboutWindow:
    """About information panel..."""

    def __init__(self, parent, translation_service, theme_service, theme_name: str):
        self.parent = parent
        self.t = translation_service
        self.theme_service = theme_service
        self.theme_name = theme_service.normalize_theme_name(theme_name)

        self.win = Toplevel(parent)
        self.win.withdraw()
        self.win.title(self.t.get("about.title", "About"))
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        apply_app_icon(self.win)

        self.colors = self.theme_service.get_color_scheme(self.theme_name)
        self.win.configure(bg=self.colors["bg"])
        self.theme_service.apply_titlebar(self.win, self.theme_name)

        self._build_ui()

        fit_window_to_content(
            self.win,
            self.parent,
            min_width=620,
            min_height=500,
            preferred_width=620,
            preferred_height=500,
            screen_margin_x=40,
            screen_margin_y=80,
        )

        self.win.deiconify()
        self.win.lift()
        self.win.grab_set()
        self.win.focus_set()

    def _build_ui(self):
        container = dialog_frame(self.win, self.colors, padx=28, pady=24)
        container.pack(fill="both", expand=True)

        dialog_label(
            container,
            self.colors,
            text=self.t.get("ui.app_name"),
            font="MewtatorTitle",
        ).pack(anchor="w")

        dialog_label(
            container,
            self.colors,
            text=self.t.get("about.subtitle"),
            font="MewtatorSubheading",
        ).pack(anchor="w", pady=(2, 4))

        dialog_label(
            container,
            self.colors,
            text=f"{self.t.get('ui.version', 'Version')} {APP_VERSION_DISPLAY}",
            font="MewtatorBody",
            muted=True,
        ).pack(anchor="w", pady=(0, 18))

        dialog_label(
            container,
            self.colors,
            text=self.t.get("about.description"),
            font="MewtatorBody",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(0, 22))

        dialog_label(
            container,
            self.colors,
            text=self.t.get("about.disclaimer"),
            font="MewtatorBody",
            wraplength=560,
            justify="left",
            muted=True,
        ).pack(anchor="w", pady=(0, 22))

        ttk.Separator(container, orient="horizontal").pack(fill="x", pady=(0, 18))

        dialog_label(
            container,
            self.colors,
            text=self.t.get("about.credits"),
            font="MewtatorHeading",
        ).pack(anchor="w", pady=(0, 8))

        credits = [
            self.t.get("about.credit_project"),
            self.t.get("about.credit_tim"),
            self.t.get("about.credit_polymeric"),
            self.t.get("about.credit_icons"),
            self.t.get("about.credit_polish"),
            self.t.get("about.credit_intro"),
            self.t.get("about.credit_game"),
        ]

        for credit in credits:
            dialog_label(
                container,
                self.colors,
                text=f"• {credit}",
                font="MewtatorBody",
                wraplength=550,
                justify="left",
            ).pack(anchor="w", pady=2)

        button_row = dialog_frame(container, self.colors)
        button_row.pack(side="bottom", fill="x", pady=(24, 0))

        ttk.Button(
            button_row,
            text=self.t.get("messages.close"),
            command=self.win.destroy,
            cursor="hand2",
        ).pack(side="right")

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