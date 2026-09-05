import json
from pathlib import Path
from typing import List, Optional


class ModListIOService:
    JSON_EXTENSION = ".json"
    TEXT_EXTENSION = ".txt"

    def get_format(self, filepath: str) -> str:
        """Return the modlist format implied by a file extension..."""
        extension = Path(filepath).suffix.lower()
        if extension == self.JSON_EXTENSION:
            return "json"
        if extension == self.TEXT_EXTENSION:
            return "text"
        raise ValueError(
            f"Unsupported modlist file type '{extension or '<none>'}'. "
            "Use a .json or .txt file."
        )

    def export_modlist_file(
        self,
        enabled_mod_names: List[str],
        filepath: str,
        modlist_name: Optional[str] = None,
    ):
        """Export a modlist using the format selected by the file extension..."""
        if self.get_format(filepath) == "json":
            self.export_modlist(enabled_mod_names, filepath, modlist_name)
        else:
            self.export_modlist_text(enabled_mod_names, filepath)

    def import_modlist_file(self, filepath: str) -> List[str]:
        """Import a modlist using the format selected by the file extension..."""
        if self.get_format(filepath) == "json":
            return self.import_modlist(filepath)
        return self.import_modlist_text(filepath)

    def export_modlist(
        self,
        enabled_mod_names: List[str],
        filepath: str,
        modlist_name: Optional[str] = None,
    ):
        data = {
            "version": "1.0",
            "mods": enabled_mod_names,
            "name": modlist_name or "",
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_modlist(self, filepath: str) -> List[str]:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = data.get("mods")

        if not isinstance(data, list):
            raise ValueError("Invalid JSON modlist format: expected a 'mods' list")

        return self._validate_mod_names(data)

    def get_modlist_name(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return str(data.get("name", "") or "")
        return ""

    def export_modlist_text(self, enabled_mod_names: List[str], filepath: str):
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            for mod_name in enabled_mod_names:
                f.write(mod_name + "\n")

    def import_modlist_text(self, filepath: str) -> List[str]:
        mods = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                name = line.strip()
                if name:
                    mods.append(name)
        return mods

    @staticmethod
    def _validate_mod_names(mod_names) -> List[str]:
        validated = []
        for mod_name in mod_names:
            if not isinstance(mod_name, str):
                raise ValueError("Invalid JSON modlist format: mod names must be strings!")
            name = mod_name.strip()
            if name:
                validated.append(name)
        return validated
