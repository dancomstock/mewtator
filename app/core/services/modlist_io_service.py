import json
from typing import List, Optional


class ModListIOService:
    def export_modlist(self, enabled_mod_names: List[str], filepath: str, modlist_name: Optional[str] = None):
        data = {
            "version": "1.0",
            "mods": enabled_mod_names,
            "name": modlist_name or ""
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def import_modlist(self, filepath: str) -> List[str]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "mods" in data:
            return data["mods"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Invalid modlist format")

    def get_modlist_name(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return str(data.get("name", "") or "")
        return ""
    
    def export_modlist_text(self, enabled_mod_names: List[str], filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            for mod_name in enabled_mod_names:
                f.write(mod_name + "\n")
    
    def import_modlist_text(self, filepath: str) -> List[str]:
        mods = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    mods.append(name)
        return mods
