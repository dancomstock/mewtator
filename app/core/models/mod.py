from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class Mod:
    name: str
    path: str
    enabled: bool = False
    missing: bool = False
    metadata: Optional[Dict[str, Any]] = None
    preview_path: Optional[str] = None
    has_unmet_requirements: bool = False
    requirement_status: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def title(self) -> str:
        # Metadata controls the user-facing label, while name remains the
        # folder/mod ID used by modlist.txt and all mod operations... Blank or
        # missing metadata (including an empty folder) falls back to the folder
        # name so the row always has a useful label... - Tim
        for key in ("title", "name"):
            value = self.metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return self.name
    
    @property
    def author(self) -> str:
        return self.metadata.get("author", "Unknown")
    
    @property
    def version(self) -> str:
        return self.metadata.get("version", "Unknown")
    
    @property
    def description(self) -> str:
        return self.metadata.get("description", "")
    
    # TEMPORARILY DISABLED: Not functional in game yet
    # @property
    # def savefile_suffix(self) -> str:
    #     return self.metadata.get("savefile_suffix", "")
    # 
    # @property
    # def inherit_save(self) -> str:
    #     return self.metadata.get("inherit_save", "")
    
    @property
    def url(self) -> str:
        return self.metadata.get("url", "")
    
    @property
    def requirements(self) -> List[Dict[str, str]]:
        reqs = self.metadata.get("requirements", [])
        if not isinstance(reqs, list):
            return []
        return reqs
    
    @property
    def dll_order(self) -> Optional[List[str]]:
        """Get the DLL load order from metadata, if specified."""
        dll_order = self.metadata.get("dll_order", [])
        if not isinstance(dll_order, list):
            return None
        return dll_order if dll_order else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "missing": self.missing,
            "metadata": self.metadata,
            "preview_path": self.preview_path,
        }
