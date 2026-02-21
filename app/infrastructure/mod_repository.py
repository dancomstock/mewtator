import json
import os
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path


class ModRepository:
    def __init__(self, mod_folder: str):
        self.mod_folder = mod_folder
        self.modlist_path = os.path.join(mod_folder, "modlist.txt")
        self._ensure_folder_structure()
    
    def _ensure_folder_structure(self):
        os.makedirs(self.mod_folder, exist_ok=True)
        if not os.path.exists(self.modlist_path):
            with open(self.modlist_path, "w", encoding="utf-8") as f:
                f.write("")
    
    def load_enabled_mod_names(self) -> List[str]:
        if not os.path.exists(self.modlist_path):
            return []
        
        mods = []
        with open(self.modlist_path, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    mods.append(name)
        return mods
    
    def save_enabled_mod_names(self, mod_names: List[str]):
        with open(self.modlist_path, "w", encoding="utf-8") as f:
            for name in mod_names:
                f.write(name + "\n")
    
    def get_mod_folders(self) -> List[str]:
        if not os.path.isdir(self.mod_folder):
            return []
        
        return sorted([
            d for d in os.listdir(self.mod_folder)
            if os.path.isdir(os.path.join(self.mod_folder, d))
        ])
    
    def load_mod_metadata(self, mod_name: str) -> Tuple[Dict[str, Any], Optional[str]]:
        mod_path = os.path.join(self.mod_folder, mod_name)
        
        if not os.path.isdir(mod_path):
            return {}, None
        
        desc_path = os.path.join(mod_path, "description.json")
        metadata = {}
        
        if os.path.isfile(desc_path):
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
    
    def get_modlist_mtime(self) -> float:
        if os.path.exists(self.modlist_path):
            return os.path.getmtime(self.modlist_path)
        return 0
