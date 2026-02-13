from tkinter import (
    Toplevel, Label, Entry, Button, filedialog, messagebox, Frame, END
)
import os
import sys
import json
from pathlib import Path

from app.autodetectgameinstall import auto_detect_game_install
from app.configloader import save_config


def get_executable_dir():
    """
    Returns the directory of the running executable.
    Works for both PyInstaller builds and source execution.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_settings_window(root, config_path, on_save_callback):
    """
    Settings window that ONLY updates:
        - game_install_dir
        - mod_folder

    All hash fields and flags remain untouched.
    """

    # Load existing config
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    win = Toplevel(root)
    win.title("Settings")
    win.geometry("600x260")
    win.resizable(False, False)

    # ---------------------------------------------------------
    # Row builder
    # ---------------------------------------------------------
    def make_row(parent, label_text):
        row = Frame(parent)
        row.pack(fill="x", padx=10, pady=5)

        lbl = Label(row, text=label_text, width=20, anchor="w")
        lbl.pack(side="left")

        entry = Entry(row, width=50)
        entry.pack(side="left", fill="x", expand=True, padx=5)

        btn = Button(row, text="Browse")
        btn.pack(side="right")

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
            messagebox.showwarning("Not Found", "Unable to detect the Mewgenics installation.")

    Button(win, text="Auto‑Detect Game Install", command=do_auto_detect).pack(pady=5)

    # ---------------------------------------------------------
    # Game Install Directory
    # ---------------------------------------------------------
    game_entry, game_btn = make_row(win, "Game Install Directory")

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
    mod_entry, mod_btn = make_row(win, "Mods Folder")

    if cfg.get("mod_folder"):
        mod_entry.insert(0, cfg["mod_folder"])

    def browse_mod():
        path = filedialog.askdirectory(parent=win)
        if path:
            mod_entry.delete(0, END)
            mod_entry.insert(0, path)

    mod_btn.config(command=browse_mod)

    # ---------------------------------------------------------
    # Save Settings
    # ---------------------------------------------------------
    def save_settings():
        game = game_entry.get().strip()
        mod = mod_entry.get().strip()

        old_game = cfg.get("game_install_dir")
        old_mod = cfg.get("mod_folder")

        if not game:
            messagebox.showerror("Error", "Game install directory is required.")
            return

        if not os.path.isdir(game):
            messagebox.showerror("Error", "Game install directory is invalid.")
            return

        if not mod:
            # Default mods folder = executable directory / mods
            exe_dir = get_executable_dir()
            mod = os.path.join(exe_dir, "mods")

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

        save_config(config_path, cfg)

        changed = {
            "game_changed": (game != old_game),
            "mods_changed": (mod != old_mod)
        }

        win.destroy()
        on_save_callback(cfg, changed)

    Button(win, text="Save Settings", command=save_settings).pack(pady=15)
