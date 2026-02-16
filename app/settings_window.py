from tkinter import (
    Toplevel, Label, Entry, Button, filedialog, messagebox, Frame, END, StringVar
)
from tkinter import ttk
import os
import sys
import json
from pathlib import Path

from app.autodetectgameinstall import auto_detect_game_install
from app.configloader import save_config
from app.i18n import init_translator, t


def get_executable_dir():
    """
    Returns the directory of the running executable.
    Works for both PyInstaller builds and source execution.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_available_languages():
    # Handle both frozen (PyInstaller) and normal execution
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - locales next to .exe
        lang_dir = Path(sys.executable).parent / "locales"
    else:
        # Running as script - locales in project root
        lang_dir = Path(__file__).parent.parent / "locales"
    
    langs = []
    if lang_dir.exists():
        for file in lang_dir.glob("*.json"):
            langs.append(file.stem)  # "English", "fr", "de"
    
    if not langs:
        return ["English"]
    
    # Sort alphabetically
    langs = sorted(langs)
    
    # Move English to the top if it exists
    if "English" in langs:
        langs.remove("English")
        langs.insert(0, "English")
    
    return langs


def show_language_selection_dialog(root):
    """
    Show a simple language selection dialog on startup.
    Returns the selected language code, or None if cancelled.
    """
    win = Toplevel(root)
    win.title(t("window.please_wait"))
    win.geometry("400x200")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    
    # Prevent closing without selection
    def on_closing():
        pass
    win.protocol("WM_DELETE_WINDOW", on_closing)
    
    result = [None]
    
    Label(win, text=t("settings.select_language_title", "Select Language"), font=("Arial", 14, "bold")).pack(pady=15)
    Label(win, text=t("settings.select_language_text", "Choose your preferred language:")).pack(pady=5)
    
    available_langs = get_available_languages()
    if not available_langs:
        available_langs = ["English"]  # Fallback if no languages found
    
    lang_var = StringVar(value=available_langs[0])
    
    # Use ttk.Combobox for better Wine/Proton compatibility
    lang_menu = ttk.Combobox(win, textvariable=lang_var, values=available_langs, state="readonly", width=30, height=15)
    lang_menu.pack(pady=10)
    
    def confirm():
        result[0] = lang_var.get()
        win.destroy()
    
    # Larger button for touch/controller input
    confirm_btn = Button(win, text=t("settings.confirm", "Confirm"), command=confirm, width=20, height=2)
    confirm_btn.pack(pady=15)
    
    # Keyboard shortcuts
    win.bind("<Return>", lambda e: confirm())
    win.bind("<KP_Enter>", lambda e: confirm())
    
    # Set focus to combobox
    lang_menu.focus_set()
    
    win.wait_window()
    return result[0]


def open_settings_window(root, config_path, on_save_callback):
    # Load existing config
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    win = Toplevel(root)
    win.title(t("settings.title", "Settings"))
    win.geometry("700x340")  # Larger for touch/controller
    win.resizable(False, False)
    win.grab_set()
    win.transient(root)


    # ---------------------------------------------------------
    # Row builder
    # ---------------------------------------------------------
    def make_row(parent, label_text):
        row = Frame(parent)
        row.pack(fill="x", padx=10, pady=5)

        lbl = Label(row, text=label_text, width=20, anchor="w")
        lbl.pack(side="left")

        entry = Entry(row, width=50, font=("Arial", 10))
        entry.pack(side="left", fill="x", expand=True, padx=5)

        # Larger button for touch/controller
        btn = Button(row, text=t("settings.browse"), width=12, height=1)
        btn.pack(side="right", padx=2)

        return entry, btn

    # ---------------------------------------------------------
    # Auto‑Detect Button
    # ---------------------------------------------------------
    def do_auto_detect():
        detected = auto_detect_game_install()
        if detected:
            game_entry.delete(0, END)
            game_entry.insert(0, detected)

            # Automatically set mod folder to the executable directory
            exe_dir = get_executable_dir()
            mod_entry.delete(0, END)
            mod_entry.insert(0, os.path.join(exe_dir, "mods"))
        else:
            messagebox.showwarning(t("messages.game_dir_not_found"), t("messages.game_dir_not_detected"))

    # Larger button for touch/controller
    auto_detect_btn = Button(win, text=t("settings.auto_detect"), command=do_auto_detect, width=25, height=2)
    auto_detect_btn.pack(pady=10)

    # ---------------------------------------------------------
    # Game Install Directory
    # ---------------------------------------------------------
    game_entry, game_btn = make_row(win, t("settings.game_install_dir"))

    if cfg.get("game_install_dir"):
        game_entry.insert(0, cfg["game_install_dir"])

    def browse_game():
        path = filedialog.askdirectory(parent=win)
        if path:
            game_entry.delete(0, END)
            game_entry.insert(0, path)

            # Automatically set mod folder to the executable directory
            exe_dir = get_executable_dir()
            mod_entry.delete(0, END)
            mod_entry.insert(0, os.path.join(exe_dir, "mods"))

    game_btn.config(command=browse_game)

    # ---------------------------------------------------------
    # Mods Folder
    # ---------------------------------------------------------
    mod_entry, mod_btn = make_row(win, t("settings.mods_folder"))

    if cfg.get("mod_folder"):
        mod_entry.insert(0, cfg["mod_folder"])

    def browse_mod():
        path = filedialog.askdirectory(parent=win)
        if path:
            mod_entry.delete(0, END)
            mod_entry.insert(0, path)

    mod_btn.config(command=browse_mod)

    # ---------------------------------------------------------
    # Language Selection
    # ---------------------------------------------------------
    lang_row = Frame(win)
    lang_row.pack(fill="x", padx=10, pady=5)

    Label(lang_row, text=t("settings.language"), width=20, anchor="w").pack(side="left")

    available_langs = get_available_languages()
    current_lang = cfg.get("language", "English")

    lang_var = StringVar(value=current_lang)

    # Use ttk.Combobox for better Wine/Proton compatibility
    lang_menu = ttk.Combobox(lang_row, textvariable=lang_var, values=available_langs, state="readonly", width=25, height=15)
    lang_menu.pack(side="left", padx=5)


    # ---------------------------------------------------------
    # Save Settings
    # ---------------------------------------------------------
    def save_settings():
        game = game_entry.get().strip()
        mod = mod_entry.get().strip()
        language = lang_var.get()

        old_game = cfg.get("game_install_dir")
        old_mod = cfg.get("mod_folder")
        old_lang = cfg.get("language", "English")

        if not game:
            messagebox.showerror(t("messages.error"), t("messages.game_dir_required"))
            return

        # Normalize game path
        game = os.path.normpath(game)

        if not os.path.isdir(game):
            messagebox.showerror(t("messages.error"), t("messages.game_dir_invalid"))
            return

        if not mod:
            # Default mods folder = executable directory / mods
            exe_dir = get_executable_dir()
            mod = os.path.join(exe_dir, "mods")
        else:
            # Normalize mod path
            mod = os.path.normpath(mod)

        # Ensure mods folder exists
        os.makedirs(mod, exist_ok=True)

        # Ensure modlist.txt exists
        modlist_path = os.path.join(mod, "modlist.txt")
        if not os.path.exists(modlist_path):
            with open(modlist_path, "w", encoding="utf-8") as f:
                f.write("")

        # Only update path fields
        cfg["game_install_dir"] = game
        cfg["mod_folder"] = mod
        cfg["language"]  = language

        save_config(config_path, cfg)

        init_translator(language)

        changed = {
            "game_changed": (game != old_game),
            "mods_changed": (mod != old_mod),
            "language_changed": (language != old_lang)
        }

        win.destroy()
        on_save_callback(cfg, changed)

    # Larger button for touch/controller
    save_btn = Button(win, text=t("settings.save", "Save Settings"), command=save_settings, width=25, height=2)
    save_btn.pack(pady=15)
    
    # Keyboard shortcuts for controller/keyboard users
    win.bind("<Return>", lambda e: save_settings() if e.widget != game_entry and e.widget != mod_entry else None)
    win.bind("<KP_Enter>", lambda e: save_settings() if e.widget != game_entry and e.widget != mod_entry else None)
    win.bind("<Escape>", lambda e: win.destroy())
    
    # Add controller hint label
    hint_label = Label(win, text=t("settings.shortcuts", "Shortcuts: Enter=Save • Esc=Cancel • Tab=Navigate"), 
                       font=("Arial", 9), fg="gray")
    hint_label.pack(pady=(0, 5))
    
    # Set initial focus to first entry
    game_entry.focus_set()
