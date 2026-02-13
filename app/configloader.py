import json
import os

def load_config(config_path):
    if not os.path.exists(config_path):
        return None  # triggers first-run settings window

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Extract paths
    game_install = cfg.get("game_install_dir", "").strip()
    mod_folder = cfg.get("mod_folder", "").strip()

    # If game path missing → force settings window
    if not game_install:
        return None

    # Default mods folder = program directory / mods
    if not mod_folder:
        mod_folder = os.path.join(os.getcwd(), "mods")

    # Ensure mods folder exists
    os.makedirs(mod_folder, exist_ok=True)

    # Ensure modlist.txt exists
    modlist_path = os.path.join(mod_folder, "modlist.txt")
    if not os.path.exists(modlist_path):
        with open(modlist_path, "w", encoding="utf-8") as f:
            f.write("")

    # Update cfg with corrected paths
    cfg["game_install_dir"] = game_install
    cfg["mod_folder"] = mod_folder

    return cfg



def save_config(config_path, cfg):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def validate_config(cfg):
    if not cfg:
        return False

    game = cfg.get("game_install_dir", "")
    mod = cfg.get("mod_folder", "")

    if not game or not os.path.isdir(game):
        return False

    if not mod:
        return False

    # mod folder may not exist yet — that’s fine, we create it later
    return True

