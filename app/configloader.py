import json
import os

def load_config(config_path):
    """
    Load config from file. Creates a default config if missing or invalid.
    Returns a valid config dict or None if required paths are missing.
    """
    
    # Default config template
    default_config = {
        "game_install_dir": "",
        "mod_folder": "",
        "language": ""
    }
    
    # Check if file exists
    if not os.path.exists(config_path):
        # Create new config file with defaults
        save_config(config_path, default_config)
        return None  # triggers settings window for paths
    
    # Try to load and parse JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, IOError):
        # Invalid JSON or file read error - replace with default
        save_config(config_path, default_config)
        return None
    
    # Validate structure - ensure required keys exist
    if not isinstance(cfg, dict):
        save_config(config_path, default_config)
        return None
    
    for key in default_config.keys():
        if key not in cfg:
            cfg[key] = default_config[key]
    
    # Extract paths
    game_install = cfg.get("game_install_dir", "").strip()
    mod_folder = cfg.get("mod_folder", "").strip()

    # If game path missing → force settings window
    if not game_install:
        return None

    # Normalize paths for cross-platform compatibility
    game_install = os.path.normpath(game_install)

    # Default mods folder = program directory / mods
    if not mod_folder:
        mod_folder = os.path.join(os.getcwd(), "mods")
    else:
        mod_folder = os.path.normpath(mod_folder)

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

