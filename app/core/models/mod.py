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
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def title(self) -> str:
        return self.metadata.get("title") or self.metadata.get("name") or self.name
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "missing": self.missing,
            "metadata": self.metadata,
            "preview_path": self.preview_path,
        }
