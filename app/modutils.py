import os
import shutil
from pathlib import Path


# ---------------------------------------------------------
# Load modlist.txt (one mod folder name per line)
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
# Merge a mod folder into the unpacked base resources
# ---------------------------------------------------------
def merge_mod_into_unpack(unpacked_root, mod_path):
    """
    Merge the contents of mod_path into unpacked_root.
    Files in the mod overwrite files in the unpacked base.
    """
    unpacked_root = Path(unpacked_root)
    mod_path = Path(mod_path)

    if not mod_path.exists():
        return

    for src in mod_path.rglob("*"):
        if src.is_file():
            rel = src.relative_to(mod_path)
            dest = unpacked_root / rel

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


# ---------------------------------------------------------
# Utility: ensure a directory exists
# ---------------------------------------------------------
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
