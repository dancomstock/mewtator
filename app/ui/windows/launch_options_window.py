import tkinter as tk

from app.ui.components.rounded_button import RoundedButton
from app.ui.layout_utils import fit_window_to_content

class _ThemedDialogBase:
    """Shared stuff for launch/export windows..."""

    def __init__(self, parent, title: str, theme_service):
        self.parent = parent
        self.theme_service = theme_service
        self.colors = theme_service.get_color_scheme(theme_service.get_current_theme())

        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        self.win.title(title)
        self.win.configure(background=self.colors["bg"])
        self.win.bind("<Escape>", lambda _event: self.win.destroy())
        theme_service.apply_titlebar(self.win, theme_service.get_current_theme())

    def _body(self, padx: int = 26, pady: int = 24):
        body = tk.Frame(
            self.win,
            background=self.colors["bg"],
            padx=padx,
            pady=pady,
        )

        body.pack(fill="both", expand=True)
        return body

    def _text_box(self, parent, *, height: int, editable: bool = False):
        text = tk.Text(
            parent,
            wrap="word",
            height=height,
            font=("Consolas", 10),
            foreground=self.colors["text_fg"],
            background=self.colors["text_bg"],
            insertbackground=self.colors["fg"],
            selectbackground=self.colors["select_bg"],
            selectforeground=self.colors["select_fg"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.colors["menu_active_bg"],
            highlightcolor=self.colors["select_bg"],
            padx=12,
            pady=10,
        )

        if not editable:
            text.configure(cursor="arrow")

        return text

    def _button(self, parent, text: str, command, width: int = 180):
        button = RoundedButton(
            parent,
            text=text,
            font="MewtatorBodyBold",
            width=width,
            height=42,
            radius=8,
            command=command,
        )

        button.apply_theme(self.colors)
        return button

    def _show_centered(self, width: int, height: int, min_width: int = None, min_height: int = None):
        fit_window_to_content(
            self.win,
            self.parent,
            min_width=min_width or 0,
            min_height=min_height or 0,
            preferred_width=width,
            preferred_height=height,
            screen_margin_x=40,
            screen_margin_y=80,
            set_minsize=True,
        )

        try:
            if self.parent.winfo_viewable():
                self.win.transient(self.parent)
        except tk.TclError:
            pass

        self.win.deiconify()
        self.win.lift()


class LaunchOptionsWindow(_ThemedDialogBase):
    """Launch-options viewer with copy and export actions..."""

    def __init__(
        self,
        parent,
        translation_service,
        theme_service,
        launch_options: str,
        on_export,
    ):
        self.t = translation_service
        self.launch_options = launch_options
        self.on_export = on_export

        super().__init__(
            parent,
            self.t.get("messages.launch_options_title", "Steam Launch Options"),
            theme_service,
        )

        self.win.resizable(True, True)
        self._build()
        self._show_centered(760, 560, min_width=650, min_height=470)

    def _build(self):
        body = self._body()

        tk.Label(
            body,
            text=self.t.get("messages.launch_options_title", "Steam Launch Options"),
            font="MewtatorHeading",
            foreground=self.colors["fg"],
            background=self.colors["bg"],
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            body,
            text=self.t.get("messages.launch_options_instructions", ""),
            font="MewtatorBody",
            foreground=self.colors["fg"],
            background=self.colors["bg"],
            justify="left",
            anchor="w",
            wraplength=700,
        ).pack(fill="x", pady=(10, 14))

        text_widget = self._text_box(body, height=12, editable=True)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", self.launch_options)

        button_row = tk.Frame(body, background=self.colors["bg"])
        button_row.pack(fill="x", pady=(18, 0))

        close_button = self._button(
            button_row,
            self.t.get("messages.close", "Close"),
            self.win.destroy,
            width=140,
        )

        close_button.pack(side="right")

        export_button = self._button(
            button_row,
            self.t.get("messages.export_bat", "Export to .BAT File"),
            lambda: self.on_export(self.win),
            width=190,
        )

        export_button.pack(side="right", padx=(0, 10))

        copy_button = self._button(
            button_row,
            self.t.get("messages.copy_to_clipboard", "Copy to Clipboard"),
            self._copy,
            width=180,
        )

        copy_button.pack(side="right", padx=(0, 10))
        copy_button.focus_set()

    def _copy(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.launch_options)
        self.parent.update()

class ExportSuccessWindow(_ThemedDialogBase):
    """Export confirmation that exposes Steam launch line..."""

    def __init__(
        self,
        parent,
        translation_service,
        theme_service,
        steam_launch_option: str,
    ):
        self.t = translation_service
        self.steam_launch_option = steam_launch_option

        super().__init__(
            parent,
            self.t.get("messages.export_bat_success_title", "Export Successful"),
            theme_service,
        )

        self.win.resizable(True, False)
        self._build()
        self._show_centered(700, 455, min_width=620, min_height=430)

    def _build(self):
        body = self._body()

        tk.Label(
            body,
            text=self.t.get("messages.export_bat_success", "Export Successful!"),
            font="MewtatorHeading",
            foreground=self.colors["fg"],
            background=self.colors["bg"],
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            body,
            text=self.t.get("messages.export_bat_instructions", ""),
            font="MewtatorBody",
            foreground=self.colors["fg"],
            background=self.colors["bg"],
            justify="left",
            anchor="w",
            wraplength=650,
        ).pack(fill="x", pady=(10, 12))

        steam_text = self._text_box(body, height=3)
        steam_text.pack(fill="x")
        steam_text.insert("1.0", self.steam_launch_option)
        steam_text.configure(state="disabled")

        tk.Label(
            body,
            text=self.t.get("messages.export_bat_note", ""),
            font="MewtatorSmall",
            foreground=self.colors["muted_fg"],
            background=self.colors["bg"],
            justify="left",
            anchor="w",
            wraplength=650,
        ).pack(fill="x", pady=(12, 16))

        button_row = tk.Frame(body, background=self.colors["bg"])
        button_row.pack(fill="x")

        close_button = self._button(
            button_row,
            self.t.get("messages.close", "Close"),
            self.win.destroy,
            width=140,
        )

        close_button.pack(side="right")

        copy_button = self._button(
            button_row,
            self.t.get("messages.copy_to_clipboard", "Copy to Clipboard"),
            self._copy,
            width=180,
        )

        copy_button.pack(side="right", padx=(0, 10))
        copy_button.focus_set()

    def _copy(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.steam_launch_option)
        self.parent.update()