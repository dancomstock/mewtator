from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Mod:
    name: str
    path: str
    enabled: bool = False
    missing: bool = False
    metadata: Optional[Dict[str, Any]] = None
    preview_path: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def title(self) -> str:
        return self.metadata.get("title", self.name)
    
    @property
    def author(self) -> str:
        return self.metadata.get("author", "Unknown")
    
    @property
    def version(self) -> str:
        return self.metadata.get("version", "Unknown")
    
    @property
    def description(self) -> str:
        return self.metadata.get("description", "")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "missing": self.missing,
            "metadata": self.metadata,
            "preview_path": self.preview_path,
        }
