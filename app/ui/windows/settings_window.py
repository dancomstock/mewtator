from tkinter import Toplevel, END, StringVar, BooleanVar, filedialog, messagebox
from tkinter import ttk
from typing import Callable
import os


class SettingsWindow:
    def __init__(self, parent, config, translation_service, theme_service, on_save: Callable):
        self.config = config
        self.translation_service = translation_service
        self.theme_service = theme_service
        self.on_save = on_save
        
        self.win = Toplevel(parent)
        self.win.title(translation_service.get("settings.title", "Settings"))
        self.win.geometry("700x700")
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.transient(parent)

        self._apply_theme()
        
        self._build_ui()

    def _apply_theme(self):
        theme_name = self.theme_service.normalize_theme_name(self.config.theme)
        colors = self.theme_service.get_color_scheme(theme_name)
        self.win.configure(bg=colors["bg"])
        self.theme_service.apply_titlebar(self.win, theme_name)

        style = ttk.Style(self.win)
        hint_color = "#9a9a9a" if theme_name == "dark" else "#666666"
        style.configure("Hint.TLabel", foreground=hint_color, background=colors["bg"])
    
    def _build_ui(self):
        t = self.translation_service
        
        auto_detect_btn = ttk.Button(
            self.win,
            text=t.get("settings.auto_detect"),
            command=self._auto_detect,
            width=25
        )
        auto_detect_btn.pack(pady=10)
        
        self.game_entry, game_btn = self._make_row(t.get("settings.game_install_dir"))
        if self.config.game_install_dir:
            self.game_entry.insert(0, self.config.game_install_dir)
        game_btn.config(command=self._browse_game)
        
        self.mod_entry, mod_btn = self._make_row(t.get("settings.mods_folder"))
        if self.config.mod_folder:
            self.mod_entry.insert(0, self.config.mod_folder)
        mod_btn.config(command=self._browse_mod)
        
        lang_row = ttk.Frame(self.win)
        lang_row.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(lang_row, text=t.get("settings.language"), width=20, anchor="w").pack(side="left")
        
        from app.infrastructure.translation_repository import TranslationRepository
        available_langs = TranslationRepository().get_available_languages()
        
        self.lang_var = StringVar(value=self.config.language)
        
        lang_menu = ttk.Combobox(
            lang_row,
            textvariable=self.lang_var,
            values=available_langs,
            state="readonly",
            width=25,
            height=15
        )
        lang_menu.pack(side="left", padx=5)
        
        self._add_separator(t.get("settings.launch_options", "Launch Options"))
        
        self.custom_launch_entry, _ = self._make_row(t.get("settings.custom_launch_options", "Custom Launch Options"), has_button=False)
        if self.config.custom_launch_options:
            self.custom_launch_entry.insert(0, self.config.custom_launch_options)
        
        checkbox_frame = ttk.Frame(self.win)
        checkbox_frame.pack(fill="x", padx=30, pady=5)
        
        self.dev_mode_var = BooleanVar(value=self.config.dev_mode_enabled)
        dev_mode_check = ttk.Checkbutton(
            checkbox_frame,
            text=t.get("settings.dev_mode", "Enable Dev Mode (-dev_mode true)"),
            variable=self.dev_mode_var
        )
        dev_mode_check.pack(anchor="w")
        
        self.debug_console_var = BooleanVar(value=self.config.debug_console_enabled)
        debug_console_check = ttk.Checkbutton(
            checkbox_frame,
            text=t.get("settings.debug_console", "Enable Debug Console (-enable_debugconsole true)"),
            variable=self.debug_console_var
        )
        debug_console_check.pack(anchor="w")
        
        # TEMPORARILY DISABLED: These features are not yet functional in the game
        # # Mod Launch Settings Overrides Section
        # self._add_separator(t.get("settings.mod_overrides", "Mod Launch Settings Overrides"))
        # 
        # self.savefile_suffix_entry, _ = self._make_row(t.get("settings.savefile_suffix_override", "Savefile Suffix Override"), has_button=False)
        # if self.config.savefile_suffix_override:
        #     self.savefile_suffix_entry.insert(0, self.config.savefile_suffix_override)
        # 
        # self.inherit_save_entry, _ = self._make_row(t.get("settings.inherit_save_override", "Inherit Save Override"), has_button=False)
        # if self.config.inherit_save_override:
        #     self.inherit_save_entry.insert(0, self.config.inherit_save_override)
        
        # Advanced Section
        self._add_separator(t.get("settings.advanced", "Advanced"))
        
        advanced_frame = ttk.Frame(self.win)
        advanced_frame.pack(fill="x", padx=30, pady=5)
        
        self.use_original_order_var = BooleanVar(value=self.config.use_original_load_order)
        use_original_order_check = ttk.Checkbutton(
            advanced_frame,
            text=t.get("settings.use_original_load_order", "Use Original Load Order (Top Priority)"),
            variable=self.use_original_order_var
        )
        use_original_order_check.pack(anchor="w")
        
        self.close_on_launch_var = BooleanVar(value=self.config.close_on_launch)
        close_on_launch_check = ttk.Checkbutton(
            advanced_frame,
            text=t.get("settings.close_on_launch", "Close Launcher When Game Launches"),
            variable=self.close_on_launch_var
        )
        close_on_launch_check.pack(anchor="w")
        
        save_btn = ttk.Button(
            self.win,
            text=t.get("settings.save", "Save Settings"),
            command=self._save_settings,
            width=25
        )
        save_btn.pack(pady=15)
        
        hint_label = ttk.Label(
            self.win,
            text=t.get("settings.shortcuts", "Shortcuts: Enter=Save • Esc=Cancel • Tab=Navigate"),
            font=("Arial", 9),
            style="Hint.TLabel"
        )
        hint_label.pack(pady=(0, 5))
        
        self.win.bind("<Return>", lambda e: self._save_settings() if e.widget not in [self.game_entry, self.mod_entry] else None)
        self.win.bind("<KP_Enter>", lambda e: self._save_settings() if e.widget not in [self.game_entry, self.mod_entry] else None)
        self.win.bind("<Escape>", lambda e: self.win.destroy())
        
        self.game_entry.focus_set()
    
    def _add_separator(self, text: str):
        """Add a section separator with label."""
        frame = ttk.Frame(self.win)
        frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ttk.Label(
            frame,
            text=text,
            font=("Arial", 10, "bold")
        ).pack(anchor="w")
        
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(2, 0))
    
    def _make_row(self, label_text: str, has_button: bool = True):
        row = ttk.Frame(self.win)
        row.pack(fill="x", padx=10, pady=5)
        
        lbl = ttk.Label(row, text=label_text, width=20, anchor="w")
        lbl.pack(side="left")
        
        entry = ttk.Entry(row, width=50, font=("Arial", 10))
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        btn = None
        if has_button:
            btn = ttk.Button(row, text=self.translation_service.get("settings.browse"), width=12)
            btn.pack(side="right", padx=2)
        
        return entry, btn
    
    def _auto_detect(self):
        from app.utils.game_detector import auto_detect_game_install
        from app.utils.platform_utils import get_executable_dir
        
        detected = auto_detect_game_install()
        if detected:
            self.game_entry.delete(0, END)
            self.game_entry.insert(0, detected)
            
            exe_dir = get_executable_dir()
            self.mod_entry.delete(0, END)
            self.mod_entry.insert(0, os.path.join(exe_dir, "mods"))
        else:
            messagebox.showwarning(
                self.translation_service.get("messages.game_dir_not_found"),
                self.translation_service.get("messages.game_dir_not_detected")
            )
    
    def _browse_game(self):
        from app.utils.platform_utils import get_executable_dir
        
        with self.theme_service.file_dialog_safe_theme():
            path = filedialog.askdirectory(parent=self.win)
        
        if path:
            self.game_entry.delete(0, END)
            self.game_entry.insert(0, path)
            
            exe_dir = get_executable_dir()
            self.mod_entry.delete(0, END)
            self.mod_entry.insert(0, os.path.join(exe_dir, "mods"))
    
    def _browse_mod(self):
        with self.theme_service.file_dialog_safe_theme():
            path = filedialog.askdirectory(parent=self.win)
        
        if path:
            self.mod_entry.delete(0, END)
            self.mod_entry.insert(0, path)
    
    def _save_settings(self):
        from app.utils.platform_utils import get_executable_dir
        
        game = self.game_entry.get().strip()
        mod = self.mod_entry.get().strip()
        language = self.lang_var.get()
        
        if not game:
            messagebox.showerror(
                self.translation_service.get("messages.error"),
                self.translation_service.get("messages.game_dir_required")
            )
            return
        
        game = os.path.normpath(game)
        
        if not os.path.isdir(game):
            messagebox.showerror(
                self.translation_service.get("messages.error"),
                self.translation_service.get("messages.game_dir_invalid")
            )
            return
        
        if not mod:
            exe_dir = get_executable_dir()
            mod = os.path.join(exe_dir, "mods")
        else:
            mod = os.path.normpath(mod)
        
        os.makedirs(mod, exist_ok=True)
        
        modlist_path = os.path.join(mod, "modlist.txt")
        if not os.path.exists(modlist_path):
            with open(modlist_path, "w", encoding="utf-8") as f:
                f.write("")
        
        self.config.game_install_dir = game
        self.config.mod_folder = mod
        self.config.language = language
        self.config.custom_launch_options = self.custom_launch_entry.get().strip()
        self.config.dev_mode_enabled = self.dev_mode_var.get()
        self.config.debug_console_enabled = self.debug_console_var.get()
        # TEMPORARILY DISABLED: These features are not yet functional in the game
        # self.config.savefile_suffix_override = self.savefile_suffix_entry.get().strip()
        # self.config.inherit_save_override = self.inherit_save_entry.get().strip()
        self.config.use_original_load_order = self.use_original_order_var.get()
        self.config.close_on_launch = self.close_on_launch_var.get()
        
        self.win.destroy()
        self.on_save(self.config)
