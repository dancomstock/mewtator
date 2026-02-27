from typing import List, Dict, Tuple
from app.core.models.mod import Mod
from app.core.models.mod_list import ModList
from app.infrastructure.mod_repository import ModRepository
from app.utils.version_parser import parse_requirement, check_requirement


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
    
    def validate_requirements(self, mod_list: ModList) -> List[str]:
        """
        Validate mod requirements and mark mods with unmet requirements.
        
        Returns:
            List of error messages for mods with unmet requirements.
        """
        errors = []
        enabled_mods = mod_list.enabled_mods
        
        mod_positions = {mod.name: idx for idx, mod in enumerate(enabled_mods)}
        mod_versions = {mod.name: mod.version for mod in enabled_mods}
        
        for idx, mod in enumerate(enabled_mods):
            mod.has_unmet_requirements = False
            
            if not mod.requirements:
                continue
            
            for req_item in mod.requirements:
                if isinstance(req_item, dict):
                    req_string = req_item.get('mod', '')
                    if 'version' in req_item:
                        req_string += req_item['version']
                elif isinstance(req_item, str):
                    req_string = req_item
                else:
                    continue
                
                parsed = parse_requirement(req_string)
                if not parsed:
                    errors.append(f"{mod.name}: Invalid requirement format '{req_string}'")
                    mod.has_unmet_requirements = True
                    continue
                
                req_mod_name, operator, req_version = parsed
                
                if req_mod_name not in mod_positions:
                    errors.append(f"{mod.name}: Required mod '{req_mod_name}' is not enabled")
                    mod.has_unmet_requirements = True
                    continue
                
                req_position = mod_positions[req_mod_name]
                if req_position > idx:
                    errors.append(f"{mod.name}: Required mod '{req_mod_name}' must be loaded before this mod (move it up in the list)")
                    mod.has_unmet_requirements = True
                    continue
                
                if operator and req_version:
                    req_mod_version = mod_versions.get(req_mod_name, '')
                    if not check_requirement(req_mod_version, operator, req_version):
                        errors.append(f"{mod.name}: Required mod '{req_mod_name}' version {req_mod_version} does not satisfy {operator}{req_version}")
                        mod.has_unmet_requirements = True
        
        return errors
    
    def detect_conflicts(self, mod_list: ModList, config) -> List[str]:
        """
        Detect conflicts in savefile_suffix and inherit_save settings.
        
        Returns:
            List of warning messages about conflicts.
        """
        warnings = []
        enabled_mods = mod_list.enabled_mods
        
        savefile_mods = [mod for mod in enabled_mods if mod.savefile_suffix]
        if len(savefile_mods) > 1:
            mod_names = [mod.name for mod in savefile_mods]
            if config.savefile_suffix_override:
                warnings.append(f"Multiple mods specify savefile_suffix: {', '.join(mod_names)}. Using settings override: '{config.savefile_suffix_override}'")
            else:
                winner = savefile_mods[0] if config.use_original_load_order else savefile_mods[-1]
                warnings.append(f"Multiple mods specify savefile_suffix: {', '.join(mod_names)}. Using '{winner.name}': '{winner.savefile_suffix}'")
        
        inherit_mods = [mod for mod in enabled_mods if mod.inherit_save]
        if len(inherit_mods) > 1:
            mod_names = [mod.name for mod in inherit_mods]
            if config.inherit_save_override:
                warnings.append(f"Multiple mods specify inherit_save: {', '.join(mod_names)}. Using settings override: '{config.inherit_save_override}'")
            else:
                winner = inherit_mods[0] if config.use_original_load_order else inherit_mods[-1]
                warnings.append(f"Multiple mods specify inherit_save: {', '.join(mod_names)}. Using '{winner.name}': '{winner.inherit_save}'")
        
        return warnings
    
    def auto_sort(self, mod_list: ModList) -> Tuple[List[str], List[str]]:
        """
        Sort enabled mods alphabetically, then adjust to satisfy requirements.
        
        Returns:
            Tuple of (sorted_names, warnings) where warnings contains messages about issues.
        """
        warnings = []
        enabled_mods = mod_list.enabled_mods
        
        if not enabled_mods:
            return [], []
        
        sorted_mods = sorted(enabled_mods, key=lambda m: m.name.lower())
        
        dependencies = {}  
        for mod in sorted_mods:
            deps = []
            for req_item in mod.requirements:
                if isinstance(req_item, dict):
                    req_string = req_item.get('mod', '')
                elif isinstance(req_item, str):
                    req_string = req_item
                else:
                    continue
                
                parsed = parse_requirement(req_string)
                if parsed:
                    req_mod_name, _, _ = parsed
                    deps.append(req_mod_name)
            dependencies[mod.name] = deps
        
        mod_names = [m.name for m in sorted_mods]
        changed = True
        iterations = 0
        max_iterations = len(mod_names) * len(mod_names)  
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for i, mod_name in enumerate(mod_names):
                if mod_name not in dependencies:
                    continue
                
                for dep_name in dependencies[mod_name]:
                    if dep_name not in mod_names:
                        continue 
                    
                    dep_idx = mod_names.index(dep_name)
                    if dep_idx > i:
                        mod_names.pop(dep_idx)
                        mod_names.insert(i, dep_name)
                        changed = True
                        break
        
        if iterations >= max_iterations:
            warnings.append("Circular dependencies detected. Some requirements may not be satisfied.")
        
        return mod_names, warnings

