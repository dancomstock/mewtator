import tkinter as tk
from tkinter import Menu, StringVar
from tkinter import ttk
from typing import Callable


class MenuBarComponent:
    def __init__(self, root, translation_service):
        self.root = root
        self.t = translation_service
        self.container = ttk.Frame(root, style="MenuBar.TFrame")
        self.container.pack(side="top", fill="x")
        self.menubar = Menu(self.container)
        self._file_menu = None
        self._lang_menu = None
        self._theme_menu = None
        self._file_button = None
        self._lang_button = None
        self._theme_button = None
        self._theme_var = None
    
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
        on_exit: Callable
    ):
        file_menu = Menu(self.menubar, tearoff=0)
        self._file_menu = file_menu
        
        file_menu.add_command(
            label=self.t.get("menu.file.settings"),
            command=on_settings,
            accelerator="F2"
        )
        
        file_menu.add_separator()
        
        file_menu.add_command(label=self.t.get("menu.file.import_modlist", "Import Modlist..."), command=on_import)
        file_menu.add_command(label=self.t.get("menu.file.export_modlist", "Export Modlist..."), command=on_export)
        
        file_menu.add_separator()
        
        file_menu.add_command(label=self.t.get("menu.file.unpack"), command=on_unpack)
        file_menu.add_command(label=self.t.get("menu.file.repack"), command=on_repack)
        
        file_menu.add_separator()
        
        file_menu.add_command(label=self.t.get("menu.file.open_mods"), command=on_open_mods)
        file_menu.add_command(label=self.t.get("menu.file.open_game"), command=on_open_game)
        
        file_menu.add_separator()
        
        file_menu.add_command(label=self.t.get("menu.file.launch_game"), command=on_launch, accelerator="F5")
        file_menu.add_command(
            label=self.t.get("menu.file.copy_launch_options", "Copy Launch Options (for Steam)"),
            command=on_copy_launch,
            accelerator="F3"
        )
        
        file_menu.add_separator()
        file_menu.add_command(label=self.t.get("menu.file.exit"), command=on_exit, accelerator="Ctrl+Q")
        
        if self._file_button is None:
            self._file_button = ttk.Menubutton(
                self.container,
                text=self.t.get("menu.file.label"),
                style="MenuBar.TMenubutton",
                menu=file_menu
            )
            self._file_button.pack(side="left", padx=4, pady=2)
        else:
            self._file_button.configure(text=self.t.get("menu.file.label"), menu=file_menu)
    
    def create_language_menu(self, available_languages: list, current_language: str, on_change: Callable):
        lang_menu = Menu(self.menubar, tearoff=0)
        self._lang_menu = lang_menu
        
        for lang in available_languages:
            is_current = "✓ " if lang == current_language else ""
            lang_menu.add_command(
                label=f"{is_current}{lang.upper()}",
                command=lambda l=lang: on_change(l)
            )
        
        if self._lang_button is None:
            self._lang_button = ttk.Menubutton(
                self.container,
                text=self.t.get("menu.language"),
                style="MenuBar.TMenubutton",
                menu=lang_menu
            )
            self._lang_button.pack(side="left", padx=4, pady=2)
        else:
            self._lang_button.configure(text=self.t.get("menu.language"), menu=lang_menu)
    
    def create_theme_menu(self, available_themes: list, current_theme: str, on_change: Callable):
        theme_menu = Menu(self.menubar, tearoff=0)
        self._theme_menu = theme_menu
        self._theme_var = StringVar(value=current_theme)

        for theme in available_themes:
            theme_menu.add_radiobutton(
                label=theme,
                value=theme,
                variable=self._theme_var,
                command=lambda t=theme: on_change(t)
            )

        label = self.t.get("menu.theme", "Theme")
        if self._theme_button is None:
            self._theme_button = ttk.Menubutton(
                self.container,
                text=label,
                style="MenuBar.TMenubutton",
                menu=theme_menu
            )
            self._theme_button.pack(side="left", padx=4, pady=2)
        else:
            self._theme_button.configure(text=label, menu=theme_menu)

    def update_theme_selection(self, theme_name: str):
        if self._theme_var is not None:
            self._theme_var.set(theme_name)

    def apply_theme(self, theme_service, theme_name: str):
        colors = theme_service.get_color_scheme(theme_name)
        style = ttk.Style(self.root)
        style.configure("MenuBar.TFrame", background=colors["menu_bg"])
        style.configure(
            "MenuBar.TMenubutton",
            background=colors["menu_bg"],
            foreground=colors["menu_fg"],
            padding=(8, 2)
        )
        style.map(
            "MenuBar.TMenubutton",
            background=[("active", colors["menu_active_bg"])],
            foreground=[("active", colors["menu_active_fg"])],
        )

        menus = [m for m in [self.menubar, self._file_menu, self._lang_menu, self._theme_menu] if m is not None]
        for menu in menus:
            menu.configure(
                background=colors["menu_bg"],
                foreground=colors["menu_fg"],
                activebackground=colors["menu_active_bg"],
                activeforeground=colors["menu_active_fg"]
            )
