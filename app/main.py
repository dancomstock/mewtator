import os
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from app.configloader import load_config, save_config, validate_config
from app.rebuild import check_rebuild_requirements, perform_unpack
from app.checking_window import CheckingWindow
from app.ui import build_ui, reload_ui
from app.settings_window import open_settings_window


# -----------------------------------------------------
# Helpers
# -----------------------------------------------------

def validate_game_install(cfg):
    """Return (ok, message). Ensures game folder + resources.gpak or backup exist.
       Auto-restores if backup exists but main file is missing."""
    game_dir = Path(cfg.get("game_install_dir", ""))
    gpak = game_dir / "resources.gpak"
    backup = game_dir / "resources_original.gpak"

    if not game_dir.exists():
        return False, f"Game directory does not exist:\n{game_dir}"

    # Auto-restore if backup exists but main file is missing
    # print("Looking for backup at:", backup.resolve())
    # print("Exists:", backup.exists())
    # print("Is file:", backup.is_file())
    # print("Is symlink:", backup.is_symlink())
    # try:
    #     print("Stat:", backup.stat())
    # except Exception as e:
    #     print("Stat failed:", e)


    if not gpak.exists() and backup.exists():
        try:
            backup.rename(gpak)
            print("Restore succeeded")
        except Exception as e:
            print("Restore FAILED:", e)
            return False, (
                f"resources.gpak was missing and auto-restore failed:\n{e}\n\n"
                "Please verify your game files."
            )
        return True, ""

    # If BOTH are missing → broken install
    if not gpak.exists() and not backup.exists():
        return False, (
            f"Could not find resources.gpak or resources_original.gpak in:\n{game_dir}\n\n"
            "Please verify your game install directory."
        )

    return True, ""



def ensure_mods_folder(cfg):
    """Create the mods folder and modlist.txt if they don't exist yet."""
    mod_folder = cfg.get("mod_folder", "")
    if not mod_folder:
        return

    os.makedirs(mod_folder, exist_ok=True)

    modlist_path = os.path.join(mod_folder, "modlist.txt")
    if not os.path.exists(modlist_path):
        with open(modlist_path, "w", encoding="utf-8") as f:
            f.write("")


# -----------------------------------------------------
# Startup Pipeline
# -----------------------------------------------------

def run_startup_checks(root, cfg, startup=False, force_hash=False):
    """
    Full startup pipeline:
    - Validate game install (folder + resources.gpak)
    - Ensure mods folder exists
    - Hash resources.gpak if needed
    - Detect game updates
    - Prompt for unpack if needed
    """

    # -----------------------------------------------------
    # 0. Validate game install BEFORE anything else
    # -----------------------------------------------------
    ok, msg = validate_game_install(cfg)
    if not ok:
        messagebox.showerror("Invalid Game Install", msg)

        # Open settings so user can fix the path
        open_settings_window(
            root,
            "config.json",
            lambda new_cfg, changed: reload_ui(root, new_cfg)
        )
        return cfg  # Stop startup checks here

    # -----------------------------------------------------
    # 1. Ensure mods folder + modlist.txt exist
    # -----------------------------------------------------
    ensure_mods_folder(cfg)

    # -----------------------------------------------------
    # 2. Skip hashing ONLY when:
    #    - not startup
    #    - not forced
    #    - we already have a stored hash
    #    - base is unpacked
    # -----------------------------------------------------
    mewgenics_path = Path(cfg["mod_folder"]) / "Mewgenics"
    folder_ok = mewgenics_path.exists() and any(mewgenics_path.iterdir())

    if not startup and not force_hash:
        if cfg.get("resources_hash") and folder_ok:
            return cfg


    # -----------------------------------------------------
    # 3. Perform full rebuild requirement check
    # -----------------------------------------------------
    if not cfg.get('skip_startup_hash'):
        checking = CheckingWindow(root, "Checking for game updates...")

        needs_unpack, needs_repack, new_hash, new_modlist_hash = \
            check_rebuild_requirements(cfg, root)

        checking.close()

    # -----------------------------------------------------
    # 4. If game updated → prompt to unpack
    # -----------------------------------------------------
        if needs_unpack:
            if messagebox.askyesno(
                "Game Updated",
                "The game’s resources have changed.\nUnpack base resources now?"
            ):
                perform_unpack(cfg, root, new_hash)

    return cfg


# -----------------------------------------------------
# Main Entry Point
# -----------------------------------------------------

def main():
    cfg = load_config("config.json")

    # print("CWD:", os.getcwd())
    # print("Config says:", cfg["game_install_dir"])
    # print("Resolved:", Path(cfg["game_install_dir"]).resolve())

    # for f in Path(cfg["game_install_dir"]).iterdir():
    #     print("Found:", f.name)


    root = tk.Tk()

    # -----------------------------------------------------
    # 1. Validate config BEFORE doing anything expensive
    # -----------------------------------------------------
    if not validate_config(cfg):
        messagebox.showinfo(
            "Setup Required",
            "Game paths are not configured yet.\nPlease enter your settings."
        )

        def after_settings(new_cfg, changed):
            # Mods folder changed → must unpack again (no hashing needed)
            if changed["mods_changed"]:
                if messagebox.askyesno(
                    "Mods Folder Changed",
                    "Your mods folder has changed.\nRecreate the unpacked base resources now?"
                ):
                    perform_unpack(new_cfg, root, new_cfg.get("resources_hash"))
                reload_ui(root, new_cfg)
                return

            # Game folder changed → must re-hash + full startup check
            if changed["game_changed"]:
                updated_cfg = run_startup_checks(root, new_cfg, force_hash=True)
                reload_ui(root, updated_cfg)
                return

            # Neither changed → no hashing, no unpack
            reload_ui(root, new_cfg)

        open_settings_window(root, "config.json", after_settings)
        root.mainloop()
        return

    # -----------------------------------------------------
    # 2. Normal startup → ALWAYS hash
    # -----------------------------------------------------
    cfg = run_startup_checks(root, cfg, startup=True)

    # -----------------------------------------------------
    # 3. Continue to UI
    # -----------------------------------------------------
    def reload_and_rebuild(new_cfg, changed=None):
        # Default changed dict if not provided
        if changed is None:
            changed = {"game_changed": False, "mods_changed": False}
        
        # Mods folder changed → unpack again
        if changed["mods_changed"]:
            if messagebox.askyesno(
                "Mods Folder Changed",
                "Your mods folder has changed.\nRecreate the unpacked base resources now?"
            ):
                perform_unpack(new_cfg, root, new_cfg.get("resources_hash"))
            reload_ui(root, new_cfg)
            return

        # Game folder changed → re-hash
        if changed["game_changed"]:
            updated_cfg = run_startup_checks(root, new_cfg, force_hash=True)
            reload_ui(root, updated_cfg)
            return

        # No changes → just reload UI
        reload_ui(root, new_cfg)

    build_ui(cfg, root, reload_and_rebuild)
    root.mainloop()


if __name__ == "__main__":
    main()
