import tkinter as tk
import tkinter.font as tkfont
from tkinter import Menu, StringVar
from tkinter import ttk
from typing import Callable

from app.ui.components.rounded_button import RoundedButton
from app.ui.components.pointer_menu import PointerMenu
from app.ui.icon_set import IconSet
from app.utils.resource_utils import resource_path


class MenuBarComponent:
    def __init__(self, root, translation_service):
        self.root = root
        self.t = translation_service
        self.icons = IconSet(root)
        self.container = ttk.Frame(root, style="MenuBar.TFrame")
        self.container.pack(side="top", fill="x")
        self.container.pack_propagate(False)
        self._nav_buttons = []
        self._nav_layout_job = None
        self.container.bind("<Configure>", self._layout_nav_buttons, add="+")
        self.menubar = Menu(self.container, cursor="hand2")
        self._file_menu = None
        self._lang_menu = None
        self._theme_menu = None
        self._file_button = None
        self._lang_button = None
        self._theme_button = None
        self._settings_button = None
        self._controls_button = None
        self._about_button = None
        self._settings_command = None
        self._theme_var = None
        self._language_var = None
        self._language_values = []
        self._theme_values = []
        self._language_labels = []
        self._theme_labels = []
        self._menu_check_image = None
        self._blank_menu_icon = tk.PhotoImage(master=root, width=16, height=16)
        self._open_menu = None
        self._open_button = None
        self._chevron_down = None
        self._chevron_up = None
        self.root.bind("<Button-1>", self._on_root_click, add="+")
        self.root.bind("<Escape>", self._on_escape, add="+")

    def _register_nav_button(self, button):
        """Track a nav button,lay all nav controls out responsively..."""
        if button not in self._nav_buttons:
            self._nav_buttons.append(button)
        self._schedule_nav_layout()

    def _schedule_nav_layout(self):
        if self._nav_layout_job is not None:
            try:
                self.root.after_cancel(self._nav_layout_job)
            except tk.TclError:
                pass
        self._nav_layout_job = self.root.after_idle(self._layout_nav_buttons)

    def _layout_nav_buttons(self, _event=None):
        """Wrap localized nav buttons onto additional rows when needed..."""
        self._nav_layout_job = None
        if not self._nav_buttons:
            self.container.configure(height=1)
            return

        try:
            available_width = self.container.winfo_width()
            if available_width <= 1:
                available_width = self.root.winfo_width()
            if available_width <= 1:
                available_width = self.root.winfo_screenwidth()
        except tk.TclError:
            return

        margin_x = 4
        margin_y = 4
        gap_x = 8
        gap_y = 8
        x = margin_x
        y = margin_y
        row_height = 0

        for button in self._nav_buttons:
            try:
                button.update_idletasks()
                width = max(1, button.winfo_reqwidth())
                height = max(1, button.winfo_reqheight())
            except tk.TclError:
                continue

            if x > margin_x and x + width + margin_x > available_width:
                x = margin_x
                y += row_height + gap_y
                row_height = 0

            button.place(x=x, y=y, width=width, height=height)
            x += width + gap_x
            row_height = max(row_height, height)

        self.container.configure(height=y + row_height + margin_y)

    def _toggle_menu(self, button, menu):
        """Toggle a menu beneath its button and keep its arrow in sync..."""

        if self._open_menu is menu:
            self._close_open_menu()
            return

        self._close_open_menu()
        self._open_menu = menu
        self._open_button = button
        self._refresh_dropdown_arrows()
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()

        try:
            # Keep popup alive while focus moves back to owning button.
            # Otherwise PointerMenu would unpost on FocusOut before button
            # release reaches _toggle_menu(), making a close-click cause a reopen... - Tim
            menu.post(x, y, owner=button)
        except tk.TclError:
            self._open_menu = None
            self._open_button = None
            self._refresh_dropdown_arrows()

    def _close_open_menu(self):
        menu = self._open_menu
        self._open_menu = None
        self._open_button = None
        self._refresh_dropdown_arrows()
        if menu is not None:
            try:
                menu.unpost()
            except tk.TclError:
                pass

    def _on_menu_unmap(self, menu):
        if self._open_menu is menu:
            self._open_menu = None
            self._open_button = None
            self._refresh_dropdown_arrows()

    def _on_root_click(self, event):
        if self._open_menu is None:
            return
        if event.widget in (self._open_button, self._open_menu):
            return
        self._close_open_menu()

    def _on_escape(self, _event):
        if self._open_menu is not None:
            self._close_open_menu()
            return "break"

    def _invoke_menu_command(self, command: Callable):
        """Close the active dropdown before running menu action..."""

        self._close_open_menu()
        command()

    def _flip_chevron(self, source):
        flipped = tk.PhotoImage(
            master=self.root,
            width=source.width(),
            height=source.height(),
        )

        flipped.tk.call(
            str(flipped),
            "copy",
            str(source),
            "-subsample",
            1,
            -1,
        )

        return flipped

    def _refresh_dropdown_arrows(self):
        if self._chevron_down is None or self._chevron_up is None:
            return
        for button in (
            self._file_button,
            self._lang_button,
            self._theme_button,
        ):
            if button is not None:
                image = (
                    self._chevron_up
                    if button is self._open_button
                    else self._chevron_down
                )
                button.configure(trailing_image=image)
    
    def _nav_button_width(self, text: str, dropdown: bool = False) -> int:
        """Size top navigation buttons to their localized labels and icons..."""

        try:
            font = tkfont.nametofont("MewtatorMenu", root=self.root)
            text_width = font.measure(text)
        except tk.TclError:
            text_width = max(48, len(text) * 8)
        # Excuse my magic number bullshittery... - Tim
        extras = 24 + 8 + 28
        if dropdown:
            extras += 16 + 8
        return max(92, text_width + extras)

    def _create_nav_button(self, text: str, command: Callable, dropdown: bool = False):
        return RoundedButton(
            self.container,
            text=text,
            font="MewtatorMenu",
            width=self._nav_button_width(text, dropdown),
            height=38,
            radius=9,
            command=command,
            icon_gap=7,
            # Sour Gummy's visible glyphs sit a bit too high. A 1 px adjustment keeps 
            # stuff centered with Font Awesome icons... - Tim
            content_offset_y=1 if not dropdown else 0,
        )

    def create_file_menu(
        self,
        on_settings: Callable,
        on_import: Callable,
        on_export: Callable,
        on_unpack: Callable,
        on_repack: Callable,
        on_open_mods: Callable,
        on_open_game: Callable,
        on_launch: Callable,
        on_copy_launch: Callable,
        on_stop: Callable,
        on_cleanup_dlls: Callable,
        on_exit: Callable
    ):
        file_menu = PointerMenu(self.root, cursor="hand2")
        self._file_menu = file_menu
        file_menu.bind(
            "<Unmap>",
            lambda _event, menu=file_menu: self._on_menu_unmap(menu),
            add="+",
        )
        
        file_menu.add_command(
            label=self.t.get("menu.file.settings"),
            command=lambda: self._invoke_menu_command(on_settings),
            accelerator="F2"
        )
        
        file_menu.add_separator()
        
        file_menu.add_command(
            label=self.t.get("menu.file.import_modlist", "Import Modlist..."),
            command=lambda: self._invoke_menu_command(on_import),
        )
        file_menu.add_command(
            label=self.t.get("menu.file.export_modlist", "Export Modlist..."),
            command=lambda: self._invoke_menu_command(on_export),
        )
        
        file_menu.add_separator()
        
        file_menu.add_command(
            label=self.t.get("menu.file.unpack"),
            command=lambda: self._invoke_menu_command(on_unpack),
        )
        file_menu.add_command(
            label=self.t.get("menu.file.repack"),
            command=lambda: self._invoke_menu_command(on_repack),
        )
        
        file_menu.add_separator()
        
        file_menu.add_command(
            label=self.t.get("menu.file.open_mods"),
            command=lambda: self._invoke_menu_command(on_open_mods),
        )
        file_menu.add_command(
            label=self.t.get("menu.file.open_game"),
            command=lambda: self._invoke_menu_command(on_open_game),
        )
        
        file_menu.add_separator()
        
        file_menu.add_command(
            label=self.t.get("menu.file.launch_game"),
            command=lambda: self._invoke_menu_command(on_launch),
            accelerator="F5",
        )
        file_menu.add_command(
            label=self.t.get("menu.file.copy_launch_options", "Copy Launch Options (for Steam)"),
            command=lambda: self._invoke_menu_command(on_copy_launch),
            accelerator="F3"
        )
        file_menu.add_command(
            label=self.t.get("menu.file.stop_game", "Stop Game"),
            command=lambda: self._invoke_menu_command(on_stop),
        )

        file_menu.add_separator()
        
        file_menu.add_command(
            label=self.t.get("menu.file.cleanup_dlls", "Clean Up DLL Injection"),
            command=lambda: self._invoke_menu_command(on_cleanup_dlls),
        )
        
        file_menu.add_separator()
        file_menu.add_command(
            label=self.t.get("menu.file.exit"),
            command=lambda: self._invoke_menu_command(on_exit),
            accelerator="Ctrl+Q",
        )
        
        file_label = self.t.get("menu.file.label")
        if self._file_button is None:
            self._file_button = self._create_nav_button(
                file_label,
                lambda: self._toggle_menu(self._file_button, self._file_menu),
                dropdown=True,
            )
            self._register_nav_button(self._file_button)
        else:
            self._file_button.configure(
                text=file_label,
                width=self._nav_button_width(file_label, dropdown=True),
            )
    
    def create_language_menu(self, available_languages: list, current_language: str, on_change: Callable):
        lang_menu = PointerMenu(self.root, cursor="hand2")
        self._lang_menu = lang_menu
        lang_menu.bind(
            "<Unmap>",
            lambda _event, menu=lang_menu: self._on_menu_unmap(menu),
            add="+",
        )
        self._language_var = StringVar(value=current_language)
        self._language_values = list(available_languages)
        self._language_labels = [lang.upper() for lang in available_languages]
        
        for lang, label in zip(available_languages, self._language_labels):
            lang_menu.add_command(
                label=label,
                image=self._blank_menu_icon,
                compound="left",
                command=lambda l=lang: self._select_language(l, on_change),
            )
        
        language_label = self.t.get("menu.language")
        if self._lang_button is None:
            self._lang_button = self._create_nav_button(
                language_label,
                lambda: self._toggle_menu(self._lang_button, self._lang_menu),
                dropdown=True,
            )
            self._register_nav_button(self._lang_button)
        else:
            self._lang_button.configure(
                text=language_label,
                width=self._nav_button_width(language_label, dropdown=True),
            )
        self._refresh_menu_indicators()
    
    def create_theme_menu(self, available_themes: list, current_theme: str, on_change: Callable):
        theme_menu = PointerMenu(self.root, cursor="hand2")
        self._theme_menu = theme_menu
        theme_menu.bind(
            "<Unmap>",
            lambda _event, menu=theme_menu: self._on_menu_unmap(menu),
            add="+",
        )
        self._theme_var = StringVar(value=current_theme)
        self._theme_values = list(available_themes)
        self._theme_labels = []

        for theme in available_themes:
            # Translate theme names
            theme_key = f"menu.theme_{theme}"
            theme_label = self.t.get(theme_key, theme.capitalize())
            self._theme_labels.append(theme_label)
            theme_menu.add_command(
                label=theme_label,
                image=self._blank_menu_icon,
                compound="left",
                command=lambda t=theme: self._select_theme(t, on_change),
            )

        label = self.t.get("menu.theme", "Theme")
        if self._theme_button is None:
            self._theme_button = self._create_nav_button(
                label,
                lambda: self._toggle_menu(self._theme_button, self._theme_menu),
                dropdown=True,
            )
            self._register_nav_button(self._theme_button)
        else:
            self._theme_button.configure(
                text=label,
                width=self._nav_button_width(label, dropdown=True),
            )
        self._refresh_menu_indicators()

    def create_settings_button(self, on_settings: Callable):
        """Add Settings button in the primary navigation row..."""

        self._settings_command = on_settings
        label = self.t.get("settings.title", "Settings")

        if self._settings_button is None:
            self._settings_button = self._create_nav_button(
                label,
                lambda: self._invoke_menu_command(self._settings_command),
            )
            self._register_nav_button(self._settings_button)
        else:
            self._settings_button.configure(
                text=label,
                width=self._nav_button_width(label),
                command=lambda: self._invoke_menu_command(self._settings_command),
            )

    def set_settings_action(self, command: Callable):
        self._settings_command = command
        if self._settings_button is not None:
            self._settings_button.configure(
                command=lambda: self._invoke_menu_command(self._settings_command)
            )

    def create_controls_button(self, on_controls: Callable):
        """Add Controls button in the primary navigation row..."""

        label = self.t.get("menu.controls", "Controls")

        if self._controls_button is None:
            self._controls_button = self._create_nav_button(
                label,
                lambda: self._invoke_menu_command(on_controls),
            )
            self._register_nav_button(self._controls_button)
        else:
            self._controls_button.configure(
                text=label,
                width=self._nav_button_width(label),
                command=lambda: self._invoke_menu_command(on_controls),
            )

    def create_about_button(self, on_about: Callable):
        """Add About button in the primary navigation row..."""

        label = self.t.get("menu.about", "About")

        if self._about_button is None:
            self._about_button = self._create_nav_button(
                label,
                lambda: self._invoke_menu_command(on_about),
            )
            self._register_nav_button(self._about_button)
        else:
            self._about_button.configure(
                text=label,
                width=self._nav_button_width(label),
                command=lambda: self._invoke_menu_command(on_about),
            )

    def _select_language(self, language: str, on_change: Callable):
        self._close_open_menu()
        self._language_var.set(language)
        self._refresh_menu_indicators()
        on_change(language)

    def _select_theme(self, theme_name: str, on_change: Callable):
        self._close_open_menu()
        self._theme_var.set(theme_name)
        self._refresh_menu_indicators()
        on_change(theme_name)

    def _refresh_menu_indicators(self):
        if self._menu_check_image is None:
            return

        if self._lang_menu is not None and self._language_var is not None:
            selected_language = self._language_var.get()
            for index, (language, label) in enumerate(
                zip(self._language_values, self._language_labels)
            ):
                image = (
                    self._menu_check_image
                    if language == selected_language
                    else self._blank_menu_icon
                )
                self._lang_menu.entryconfigure(
                    index,
                    label=label,
                    image=image,
                    compound="left",
                )

        if self._theme_menu is not None and self._theme_var is not None:
            selected_theme = self._theme_var.get()
            for index, (theme_name, label) in enumerate(
                zip(self._theme_values, self._theme_labels)
            ):
                image = (
                    self._menu_check_image
                    if theme_name == selected_theme
                    else self._blank_menu_icon
                )
                self._theme_menu.entryconfigure(
                    index,
                    label=label,
                    image=image,
                    compound="left",
                )

    def update_theme_selection(self, theme_name: str):
        if self._theme_var is not None:
            self._theme_var.set(theme_name)
            self._refresh_menu_indicators()

    def _load_unicode_check(self, theme_name: str):
        """Load sexy antialiased U+2713 menu glyph..."""
        theme = "dark"
        
        return tk.PhotoImage(
            master=self.root,
            file=resource_path(
                "assets",
                "icons",
                "unicode",
                theme,
                "check.png",
            ),
        )

    def apply_theme(self, theme_service, theme_name: str):
        colors = theme_service.get_color_scheme(theme_name)
        self._menu_check_image = self._load_unicode_check(theme_name)
        style = ttk.Style(self.root)
        style.configure("MenuBar.TFrame", background=colors["menu_bg"])

        self._chevron_down = self.icons.get("chevron-down", theme_name)
        self._chevron_up = self._flip_chevron(self._chevron_down)

        for button in (
            self._file_button,
            self._lang_button,
            self._theme_button,
            self._settings_button,
            self._controls_button,
            self._about_button,
        ):
            if button is not None:
                button.apply_theme(colors)

        if self._file_button is not None:
            self._file_button.configure(
                image=self.icons.get("folder-open", theme_name),
                trailing_image=self._chevron_down,
            )
        if self._lang_button is not None:
            self._lang_button.configure(
                image=self.icons.get("language", theme_name),
                trailing_image=self._chevron_down,
            )
        if self._theme_button is not None:
            self._theme_button.configure(
                image=self.icons.get("paint-brush", theme_name),
                trailing_image=self._chevron_down,
            )
        if self._settings_button is not None:
            self._settings_button.configure(image=self.icons.get("gear", theme_name))
        if self._controls_button is not None:
            self._controls_button.configure(image=self.icons.get("sliders", theme_name))
        if self._about_button is not None:
            self._about_button.configure(image=self.icons.get("info-circle", theme_name))

        self._refresh_dropdown_arrows()

        menus = [m for m in [self.menubar, self._file_menu, self._lang_menu, self._theme_menu] if m is not None]
        for menu in menus:
            menu.configure(
                background=colors["menu_bg"],
                foreground=colors["menu_fg"],
                activebackground=colors["menu_active_bg"],
                activeforeground=colors["menu_active_fg"],
                font="MewtatorMenu",
                cursor="hand2",
            )
        self._refresh_menu_indicators()
        self._schedule_nav_layout()
