import tkinter as tk

from app.ui.components.dialog_text import dialog_label
from app.ui.layout_utils import fit_window_to_content


class CheckingWindow:
    def __init__(self, root, title="Please wait...", message="Checking...", theme_service=None):
        if theme_service is not None:
            theme_name = theme_service.get_current_theme()
            colors = theme_service.get_color_scheme(theme_name)
        else:
            colors = {"bg": "#1c1c1c", "fg": "#e6e6e6"}

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.configure(background=colors["bg"])
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        if root.winfo_viewable():
            self.win.transient(root)

        if theme_service is not None:
            theme_service.apply_titlebar(self.win, theme_service.get_current_theme())

        label = dialog_label(
            self.win,
            colors,
            text=message,
            font="MewtatorHeading",
            wraplength=380,
            justify="center",
        )
        label.pack(expand=True, padx=20, pady=20)

        fit_window_to_content(
            self.win,
            root,
            min_width=420,
            min_height=140,
            preferred_width=420,
            preferred_height=140,
            screen_margin_x=40,
            screen_margin_y=80,
        )

        self.win.deiconify()
        self.win.lift()
        self.win.update()

    def close(self):
        self.win.destroy()
