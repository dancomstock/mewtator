import tkinter as tk

from app.ui.components.rounded_button import RoundedButton
from app.ui.layout_utils import fit_window_to_content

class NotificationWindow:
    """Small notification..."""

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        theme_service,
        button_text: str = "OK",
        cancel_text: str = None,
        kind: str = "info",
    ):
        self.parent = parent
        self.result = False

        self.colors = theme_service.get_color_scheme(
            theme_service.get_current_theme()
        )

        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.configure(background=self.colors["bg"])
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda _event: self.close())

        theme_service.apply_titlebar(
            self.win,
            theme_service.get_current_theme(),
        )

        body = tk.Frame(
            self.win,
            background=self.colors["bg"],
            padx=28,
            pady=24,
        )

        body.pack(fill="both", expand=True)

        if kind == "error":
            title_color = (
                "#ff7b82"
                if theme_service.get_current_theme() == "dark"
                else "#b42318"
            )
        elif kind == "warning":
            title_color = (
                "#f0a020"
                if theme_service.get_current_theme() == "dark"
                else "#8a5b00"
            )
        else:
            title_color = self.colors["fg"]

        tk.Label(
            body,
            text=title,
            font="MewtatorHeading",
            foreground=title_color,
            background=self.colors["bg"],
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            body,
            text=message,
            font="MewtatorBody",
            foreground=self.colors["fg"],
            background=self.colors["bg"],
            justify="left",
            anchor="w",
            wraplength=464,
        ).pack(fill="x", pady=(12, 22))

        button_row = tk.Frame(body, background=self.colors["bg"])
        button_row.pack(fill="x")

        if cancel_text is not None:
            self.cancel_button = RoundedButton(
                button_row,
                text=cancel_text,
                font="MewtatorBodyBold",
                width=120,
                height=42,
                command=lambda: self.close(False),
            )

            self.cancel_button.apply_theme(self.colors)
            self.cancel_button.pack(side="right")
        else:
            self.cancel_button = None

        self.confirm_button = RoundedButton(
            button_row,
            text=button_text,
            font="MewtatorBodyBold",
            width=120,
            height=42,
            command=lambda: self.close(True),
        )

        self.confirm_button.apply_theme(self.colors)

        self.confirm_button.pack(
            side="right",
            padx=(0, 10) if self.cancel_button is not None else 0,
        )

        fit_window_to_content(
            self.win,
            self.parent,
            min_width=520,
            preferred_width=520,
            screen_margin_x=40,
            screen_margin_y=80,
        )

        if parent.winfo_viewable():
            self.win.transient(parent)

        self.win.deiconify()
        self.win.lift()
        self.win.grab_set()

        if self.cancel_button is not None:
            self.cancel_button.focus_set()
        else:
            self.confirm_button.focus_set()

    def _center(self, width: int, height: int):
        self.parent.update_idletasks()

        if self.parent.winfo_viewable():
            x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
            y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 2
        else:
            x = (self.win.winfo_screenwidth() - width) // 2
            y = (self.win.winfo_screenheight() - height) // 2
        self.win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def show(self):
        self.parent.wait_window(self.win)
        return self.result

    def close(self, result: bool = False):
        self.result = result
        if self.win.winfo_exists():
            try:
                self.win.grab_release()
            except tk.TclError:
                pass
            self.win.destroy()