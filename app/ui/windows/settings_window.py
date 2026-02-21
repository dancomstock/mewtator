from tkinter import Toplevel, END, StringVar, filedialog, messagebox
from tkinter import ttk
from typing import Callable
import os


class SettingsWindow:
    def __init__(self, parent, config, translation_service, on_save: Callable):
        self.config = config
        self.translation_service = translation_service
        self.on_save = on_save
        
        self.win = Toplevel(parent)
        self.win.title(translation_service.get("settings.title", "Settings"))
        self.win.geometry("700x340")
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.transient(parent)
        
        self._build_ui()
    
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
            fg="gray"
        )
        hint_label.pack(pady=(0, 5))
        
        self.win.bind("<Return>", lambda e: self._save_settings() if e.widget not in [self.game_entry, self.mod_entry] else None)
        self.win.bind("<KP_Enter>", lambda e: self._save_settings() if e.widget not in [self.game_entry, self.mod_entry] else None)
        self.win.bind("<Escape>", lambda e: self.win.destroy())
        
        self.game_entry.focus_set()
    
    def _make_row(self, label_text: str):
        row = ttk.Frame(self.win)
        row.pack(fill="x", padx=10, pady=5)
        
        lbl = ttk.Label(row, text=label_text, width=20, anchor="w")
        lbl.pack(side="left")
        
        entry = ttk.Entry(row, width=50, font=("Arial", 10))
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
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
        
        path = filedialog.askdirectory(parent=self.win)
        if path:
            self.game_entry.delete(0, END)
            self.game_entry.insert(0, path)
            
            exe_dir = get_executable_dir()
            self.mod_entry.delete(0, END)
            self.mod_entry.insert(0, os.path.join(exe_dir, "mods"))
    
    def _browse_mod(self):
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
        
        self.win.destroy()
        self.on_save(self.config)
