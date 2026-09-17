import json
import os
import shutil
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path


class ModRepository:
    HIDDEN_MOD_NAMES = frozenset({"_unpacked", "unpacked_resources"})

    def __init__(self, mod_folder: str):
        self.mod_folder = mod_folder
        self.modlist_path = os.path.join(mod_folder, "modlist.txt")
        self._ensure_folder_structure()
    
    def _ensure_folder_structure(self):
        os.makedirs(self.mod_folder, exist_ok=True)
        if not os.path.exists(self.modlist_path):
            with open(self.modlist_path, "w", encoding="utf-8") as f:
                f.write("")
    
    @classmethod
    def _is_hidden_mod_name(cls, name: str) -> bool:
        return name.casefold() in cls.HIDDEN_MOD_NAMES

    def load_enabled_mod_names(self) -> List[str]:
        if not os.path.exists(self.modlist_path):
            return []
        
        mods = []
        with open(self.modlist_path, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name and not self._is_hidden_mod_name(name):
                    mods.append(name)
        return mods
    
    def save_enabled_mod_names(self, mod_names: List[str]):
        with open(self.modlist_path, "w", encoding="utf-8") as f:
            for name in mod_names:
                if not self._is_hidden_mod_name(name):
                    f.write(name + "\n")
    
    def get_mod_folders(self) -> List[str]:
        if not os.path.isdir(self.mod_folder):
            return []
        
        return sorted([
            d for d in os.listdir(self.mod_folder)
            if (
                os.path.isdir(os.path.join(self.mod_folder, d))
                and not self._is_hidden_mod_name(d)
            )
        ])
    
    def load_mod_metadata(self, mod_name: str) -> Tuple[Dict[str, Any], Optional[str]]:
        mod_path = os.path.join(self.mod_folder, mod_name)
        
        if not os.path.isdir(mod_path):
            return {}, None
        
        desc_filenames = ["description.json", "info.json", "modinfo.json"]
        desc_path = None
        
        for filename in desc_filenames:
            potential_path = os.path.join(mod_path, filename)
            if os.path.isfile(potential_path):
                desc_path = potential_path
                break
        
        metadata = {}
        
        if desc_path:
            try:
                with open(desc_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                metadata = {}
        
        preview_path = None
        for name in os.listdir(mod_path):
            ext = name.lower().split(".")[-1]
            if name.lower().startswith("preview") and ext in ("png", "jpg", "jpeg", "webp"):
                preview_path = os.path.join(mod_path, name)
                break
        
        return metadata, preview_path
    
    def mod_exists(self, mod_name: str) -> bool:
        mod_path = os.path.join(self.mod_folder, mod_name)
        return os.path.isdir(mod_path)
    
    def get_mod_path(self, mod_name: str) -> str:
        return os.path.join(self.mod_folder, mod_name)
    
    def delete_mod_folder(self, mod_name: str):
        """Permanently delete a mod folder!"""

        if (not mod_name or os.path.basename(mod_name) != mod_name or mod_name in (".", "..")):
            raise ValueError("Invalid mod folder name!")

        root = os.path.realpath(self.mod_folder)
        target = os.path.join(root, mod_name)

        # Never follow directory symlinks or allow crafted modlist entry 
        # to escape the configured mods directory... - Tim
        if os.path.islink(target):
            raise ValueError("Refusing to delete a symbolic-link mod folder!")
        resolved_target = os.path.realpath(target)
        if os.path.dirname(resolved_target) != root:
            raise ValueError("Mod folder is outside the configured mods directory!")
        if not os.path.isdir(target):
            raise FileNotFoundError(f"Mod folder not found: {mod_name}!")

        shutil.rmtree(target)
    
    def get_modlist_mtime(self) -> float:
        if os.path.exists(self.modlist_path):
            return os.path.getmtime(self.modlist_path)
        return 0

    def get_filesystem_state(self):
        """Return the externally observable mod state used by the UI watcher...
        """
        try:
            with open(self.modlist_path, "rb") as f:
                modlist_contents = f.read()
        except OSError:
            modlist_contents = None

        try:
            folder_names = tuple(sorted(
                d for d in os.listdir(self.mod_folder)
                if (
                    os.path.isdir(os.path.join(self.mod_folder, d))
                    and not self._is_hidden_mod_name(d)
                )
            ))
        except OSError:
            folder_names = ()

        metadata_filenames = ("description.json", "info.json", "modinfo.json")
        metadata_state = []
        ini_state = []

        for folder_name in folder_names:
            mod_path = os.path.join(self.mod_folder, folder_name)
            file_state = []

            for filename in metadata_filenames:
                metadata_path = os.path.join(mod_path, filename)
                try:
                    with open(metadata_path, "rb") as f:
                        contents = f.read()
                except (OSError, IsADirectoryError):
                    contents = None

                file_state.append((filename, contents))

            metadata_state.append((folder_name, tuple(file_state)))

            # Root-level ini creation/removal/edits affect whether mod settings
            # should be exposed in the selected mod's preview. Track stats for
            # every root ini without recursively scanning the mod payload... - Tim
            root_ini_files = []

            try:
                entries = sorted(
                    (
                        entry for entry in os.scandir(mod_path)
                        if entry.is_file() and entry.name.lower().endswith(".ini")
                    ),
                    key=lambda entry: entry.name.casefold(),
                )
            except OSError:
                entries = []

            for entry in entries:
                try:
                    stat = entry.stat()
                    root_ini_files.append(
                        (entry.name, stat.st_mtime_ns, stat.st_size)
                    )
                except OSError:
                    root_ini_files.append((entry.name, None, None))

            ini_state.append((folder_name, tuple(root_ini_files)))

        return (
            modlist_contents,
            folder_names,
            tuple(metadata_state),
            tuple(ini_state),
        )
