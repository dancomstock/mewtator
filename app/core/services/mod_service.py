from typing import List
from app.core.models.mod import Mod
from app.core.models.mod_list import ModList
from app.infrastructure.mod_repository import ModRepository


class ModService:
    def __init__(self, repository: ModRepository):
        self.repository = repository
    
    def load_mods(self) -> ModList:
        enabled_names = self.repository.load_enabled_mod_names()
        enabled_set = set(enabled_names)
        folder_mods = self.repository.get_mod_folders()
        
        mods = []
        
        for name in enabled_names:
            mod_path = self.repository.get_mod_path(name)
            exists = self.repository.mod_exists(name)
            
            if exists:
                metadata, preview = self.repository.load_mod_metadata(name)
            else:
                metadata, preview = {}, None
            
            mods.append(Mod(
                name=name,
                path=mod_path,
                enabled=True,
                missing=not exists,
                metadata=metadata,
                preview_path=preview,
            ))
        
        for name in folder_mods:
            if name in enabled_set:
                continue
            
            mod_path = self.repository.get_mod_path(name)
            metadata, preview = self.repository.load_mod_metadata(name)
            
            mods.append(Mod(
                name=name,
                path=mod_path,
                enabled=False,
                missing=False,
                metadata=metadata,
                preview_path=preview,
            ))
        
        return ModList(mods)
    
    def save_mod_order(self, mod_list: ModList):
        enabled_names = mod_list.enabled_mod_names
        self.repository.save_enabled_mod_names(enabled_names)
    
    def get_enabled_mod_paths(self, mod_list: ModList) -> List[str]:
        return [mod.path for mod in mod_list.enabled_mods]
    
    def get_missing_mod_names(self, mod_list: ModList) -> List[str]:
        return [mod.name for mod in mod_list.missing_mods]
