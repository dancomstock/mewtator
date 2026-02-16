import os
import json


# ---------------------------------------------------------
# Load modlist.txt (enabled mods)
# ---------------------------------------------------------
def load_mod_list(mod_folder):
    modlist_path = os.path.join(mod_folder, "modlist.txt")

    if not os.path.exists(modlist_path):
        return []

    mods = []
    with open(modlist_path, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                mods.append(name)

    return mods


# ---------------------------------------------------------
# Save modlist.txt
# ---------------------------------------------------------
def save_mod_list(mod_folder, mods):
    modlist_path = os.path.join(mod_folder, "modlist.txt")
    with open(modlist_path, "w", encoding="utf-8") as f:
        for mod in mods:
            f.write(mod + "\n")


# ---------------------------------------------------------
# Load metadata + preview for a mod
# ---------------------------------------------------------
def load_metadata(mod_path):
    desc_path = os.path.join(mod_path, "description.json")

    data = {}
    if os.path.isfile(desc_path):
        try:
            with open(desc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    preview_path = None
    for name in os.listdir(mod_path):
        ext = name.lower().split(".")[-1]
        if name.lower().startswith("preview") and ext in ("png", "jpg", "jpeg", "webp"):
            preview_path = os.path.join(mod_path, name)
            break

    return data, preview_path


# ---------------------------------------------------------
# List all mods with metadata + enabled state
# ---------------------------------------------------------
def list_mods(mod_folder):
    """
    Returns a list of mod descriptors:
    [
        {
            "name": "ModName",
            "path": "C:/mods/ModName",
            "enabled": True/False,
            "missing": True/False,
            "metadata": {...},
            "preview_path": "path/to/preview.png" or None
        }
    ]
    """

    if not mod_folder or not os.path.isdir(mod_folder):
        return []

    enabled_mods = load_mod_list(mod_folder)
    enabled_set = set(enabled_mods)

    # All folders that actually exist
    folder_mods = sorted([
        d for d in os.listdir(mod_folder)
        if os.path.isdir(os.path.join(mod_folder, d))
    ])

    mods = []

    # 1. Add enabled mods (even if missing)
    for name in enabled_mods:
        mod_path = os.path.join(mod_folder, name)
        exists = os.path.isdir(mod_path)

        metadata, preview = (load_metadata(mod_path) if exists else ({}, None))

        mods.append({
            "name": name,
            "path": mod_path,
            "enabled": True,
            "missing": not exists,
            "metadata": metadata,
            "preview_path": preview,
        })

    # 2. Add disabled mods (only those that exist)
    for name in folder_mods:
        if name in enabled_set:
            continue

        mod_path = os.path.join(mod_folder, name)
        metadata, preview = load_metadata(mod_path)

        mods.append({
            "name": name,
            "path": mod_path,
            "enabled": False,
            "missing": False,
            "metadata": metadata,
            "preview_path": preview,
        })

    return mods

