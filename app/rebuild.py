import os
import json
from pathlib import Path

from app.hashing import hash_file, hash_list
from app.configloader import save_config
from app.modutils import load_mod_list
from app.progress_window import ProgressWindow
import struct
import shutil


# ---------------------------------------------------------
# Hashing helpers for mod content
# ---------------------------------------------------------
def hash_mod_folder(mod_path: Path):
    """Hash all files inside a mod folder."""
    file_hashes = []

    for file in sorted(mod_path.rglob("*")):
        if file.is_file():
            file_hashes.append(hash_file(file))

    return hash_list(file_hashes)


def compute_modlist_hash(cfg, root):
    """
    Hash all enabled mods based on their file contents,
    with a progress window so the UI never freezes.
    """
    mod_folder = Path(cfg["mod_folder"])
    modlist = load_mod_list(cfg["mod_folder"])

    # Count total files across all mods
    all_files = []
    for mod_name in modlist:
        mod_path = mod_folder / mod_name
        if mod_path.exists():
            all_files.extend([p for p in mod_path.rglob("*") if p.is_file()])

    pw = ProgressWindow(root, "Hashing...", len(all_files))

    mod_hashes = []
    file_index = 0

    for mod_name in modlist:
        mod_path = mod_folder / mod_name
        if not mod_path.exists():
            continue

        file_hashes = []
        for file in sorted(mod_path.rglob("*")):
            if file.is_file():
                file_hashes.append(hash_file(file))
                file_index += 1
                pw.update(file_index)

        mod_hashes.append(hash_list(file_hashes))

    pw.close()
    return hash_list(mod_hashes)



# ---------------------------------------------------------
# Ensure mods/Mewgenics exists (no inner folder)
# ---------------------------------------------------------
def ensure_mewgenics_mod(cfg):
    mewgenics_path = Path(cfg["mod_folder"]) / "Mewgenics"
    mewgenics_path.mkdir(parents=True, exist_ok=True)
    return mewgenics_path


# ---------------------------------------------------------
# Write description.json so it appears in UI
# ---------------------------------------------------------
def write_mewgenics_description(mewgenics_path: Path):
    desc_path = mewgenics_path / "description.json"

    data = {
        "title": "Mewgenics Base Resources",
        "author": "Edmund McMillen, Tyler Glaiel",
        "version": "1.0",
        "description": "Automatically unpacked base game resources for mod merging."
    }

    with desc_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ---------------------------------------------------------
# Unpack directly into mods/Mewgenics/ with progress
# ---------------------------------------------------------
def unpack_with_progress(cfg, root):

    gpak_path = Path(cfg["game_install_dir"]) / "resources.gpak"
    out_dir = Path(cfg["mod_folder"]) / "Mewgenics"

    # First pass: count entries
    with gpak_path.open("rb") as f:
        count = struct.unpack("<i", f.read(4))[0]

    pw = ProgressWindow(root, "Unpacking Base Resources", count)

    # Actual unpack
    with gpak_path.open("rb") as f:
        count = struct.unpack("<i", f.read(4))[0]

        entries = []
        for _ in range(count):
            path_len = struct.unpack("<h", f.read(2))[0]
            path = f.read(path_len).decode("utf-8")
            file_len = struct.unpack("<i", f.read(4))[0]
            entries.append((path, file_len))

        for i, (path, file_len) in enumerate(entries):
            out_path = out_dir / path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            data = f.read(file_len)
            with out_path.open("wb") as out:
                out.write(data)

            pw.update(i + 1)

    pw.close()


# ---------------------------------------------------------
# Repack with progress
# ---------------------------------------------------------
def repack_with_progress(cfg, root, source_root: Path, temp_dir: Path):

    out_gpak = temp_dir / "resources_modded.gpak"
    out_gpak.parent.mkdir(parents=True, exist_ok=True)

    files = [p for p in source_root.rglob("*") if p.is_file()]
    pw = ProgressWindow(root, "Repacking Resources", len(files))

    with out_gpak.open("wb") as f:
        f.write(struct.pack("<i", len(files)))

        for relpath in files:
            rel = relpath.relative_to(source_root).as_posix()
            rel_bytes = rel.encode("utf-8")
            f.write(struct.pack("<h", len(rel_bytes)))
            f.write(rel_bytes)
            f.write(struct.pack("<i", relpath.stat().st_size))

        for i, relpath in enumerate(files):
            with relpath.open("rb") as src:
                f.write(src.read())
            pw.update(i + 1)

    pw.close()




# ---------------------------------------------------------
# Check if unpack or repack is needed
# ---------------------------------------------------------
def check_rebuild_requirements(cfg, root):
    gpak_path = Path(cfg["game_install_dir"]) / "resources.gpak"
    current_hash = hash_file(gpak_path)

    # NEW: content-aware modlist hash
    current_modlist_hash = compute_modlist_hash(cfg, root)

    # Unpack needed if base hash changed OR base folder missing/empty
    mewgenics_path = Path(cfg["mod_folder"]) / "Mewgenics"
    folder_ok = mewgenics_path.exists() and any(mewgenics_path.iterdir())

    needs_unpack = (cfg.get("resources_hash") != current_hash) or not folder_ok

    # Repack needed if modlist hash changed OR modded output missing
    temp_dir = Path(os.getcwd()) / "_temp"
    modded_gpak = temp_dir / "resources_modded.gpak"
    modded_exists = modded_gpak.exists() and modded_gpak.stat().st_size > 0

    needs_repack = (cfg.get("modlist_hash") != current_modlist_hash) or not modded_exists

    return needs_unpack, needs_repack, current_hash, current_modlist_hash



# ---------------------------------------------------------
# Full unpack pipeline (called at startup)
# ---------------------------------------------------------
def perform_unpack(cfg, root, new_hash):
    mewgenics_path = ensure_mewgenics_mod(cfg)

    # -----------------------------------------------------
    # Remove old unpacked base if it exists
    # -----------------------------------------------------
    if mewgenics_path.exists():
        import shutil
        shutil.rmtree(mewgenics_path)

    # Recreate folder
    mewgenics_path.mkdir(parents=True, exist_ok=True)

    write_mewgenics_description(mewgenics_path)
    unpack_with_progress(cfg, root)

    cfg["resources_hash"] = new_hash
    save_config("config.json", cfg)



# ---------------------------------------------------------
# Full repack pipeline (called when launching)
# ---------------------------------------------------------
def perform_repack(cfg, root, new_modlist_hash):
    program_root = Path(os.getcwd())
    build_dir = program_root / "_build"
    temp_dir = program_root / "_temp"

    # Clean build dir
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    mod_folder = Path(cfg["mod_folder"])
    base_dir = mod_folder / "Mewgenics"

    # ---------------------------------------------------------
    # 1) COPY BASE RESOURCES
    # ---------------------------------------------------------
    base_files = [p for p in base_dir.rglob("*") if p.is_file()]
    base_pw = ProgressWindow(root, "Copying Base Resources...", len(base_files))

    for i, src in enumerate(base_files):
        rel = src.relative_to(base_dir)
        dst = build_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        base_pw.update(i + 1)

    base_pw.close()

    # ---------------------------------------------------------
    # 2) MERGE MODS (same logic as base)
    # ---------------------------------------------------------
    modlist = load_mod_list(cfg["mod_folder"])
    merge_pw = ProgressWindow(root, "Merging Mods...", len(modlist))

    for i, mod_name in enumerate(modlist):
        if mod_name == "Mewgenics":
            merge_pw.update(i + 1)
            continue

        mod_path = mod_folder / mod_name
        if mod_path.exists():
            mod_files = [p for p in mod_path.rglob("*") if p.is_file()]
            for src in mod_files:
                rel = src.relative_to(mod_path)
                dst = build_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        merge_pw.update(i + 1)

    merge_pw.close()

    # ---------------------------------------------------------
    # 3) REPACK
    # ---------------------------------------------------------
    repack_with_progress(cfg, root, build_dir, temp_dir)

    # ---------------------------------------------------------
    # 4) CLEAN UP
    # ---------------------------------------------------------
    # shutil.rmtree(build_dir)

    # ---------------------------------------------------------
    # 5) UPDATE CONFIG
    # ---------------------------------------------------------
    cfg["modlist_hash"] = new_modlist_hash
    save_config("config.json", cfg)





