import tkinter as tk
from tkinter import ttk

from app.ui.components.dialog_text import dialog_label
from app.ui.layout_utils import fit_window_to_content


class ProgressWindow:
    def __init__(self, root, title, maximum, theme_service=None):
        self.theme_service = theme_service
        if theme_service is not None:
            theme_name = theme_service.get_current_theme()
            self.colors = theme_service.get_color_scheme(theme_name)
        else:
            self.colors = {
                "bg": "#1c1c1c",
                "fg": "#e6e6e6",
            }

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.configure(background=self.colors["bg"])
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        if root.winfo_viewable():
            self.win.transient(root)

        if theme_service is not None:
            theme_service.apply_titlebar(self.win, theme_service.get_current_theme())

        self.label = dialog_label(
            self.win,
            self.colors,
            text=title,
            font="MewtatorHeading",
        )
        self.label.pack(pady=10)

        self.pb = ttk.Progressbar(
            self.win,
            orient="horizontal",
            length=450,
            mode="determinate",
            maximum=maximum,
        )
        self.pb.pack(pady=10)

        self.percent_label = dialog_label(
            self.win,
            self.colors,
            text="0%",
            font="MewtatorBody",
        )
        self.percent_label.pack()

        fit_window_to_content(
            self.win,
            root,
            min_width=500,
            min_height=160,
            preferred_width=500,
            preferred_height=160,
            screen_margin_x=40,
            screen_margin_y=80,
        )

        self.win.deiconify()
        self.win.lift()
        self.win.update()

    def update(self, value):
        self.pb["value"] = value
        percent = int((value / self.pb["maximum"]) * 100)
        self.percent_label.config(text=f"{percent}%")
        self.win.update()

    def close(self):
        self.win.destroy()
