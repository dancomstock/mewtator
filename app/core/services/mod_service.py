from typing import List, Dict, Tuple
from app.core.models.mod import Mod
from app.core.models.mod_list import ModList
from app.infrastructure.mod_repository import ModRepository
from app.utils.version_parser import parse_requirement, check_requirement
from app.utils.resource_utils import resource_path


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
    
    def delete_mod(self, mod_list: ModList, mod_name: str):
        """Delete a mod folder and remove it..."""

        mod = mod_list.get_mod_by_name(mod_name)

        if mod is None:
            raise ValueError(f"Unknown mod: {mod_name}")
        if mod.missing or not self.repository.mod_exists(mod_name):
            raise FileNotFoundError(f"Mod folder not found: {mod_name}")

        original_enabled_names = mod_list.enabled_mod_names

        updated_enabled_names = [
            name for name in original_enabled_names if name != mod_name
        ]

        # Write the order first, so a permissions error cannot destroy the mod
        # while leaving enabled stale entry behind. If folder deletion then
        # fails, restore the previous order as best-effort rollback... - Tim
        if updated_enabled_names != original_enabled_names:
            self.repository.save_enabled_mod_names(updated_enabled_names)
        try:
            self.repository.delete_mod_folder(mod_name)
        except Exception:
            if updated_enabled_names != original_enabled_names:
                try:
                    self.repository.save_enabled_mod_names(original_enabled_names)
                except Exception:
                    pass
            raise
    
    def get_enabled_mod_paths(self, mod_list: ModList) -> List[str]:
        return [mod.path for mod in mod_list.enabled_mods]
    
    def get_launch_mod_paths(self, mod_list: ModList, config=None) -> List[str]:
        """Return the effective mod paths used to launch the game...
        """
        mod_paths = self.get_enabled_mod_paths(mod_list)

        intro_enabled = True if config is None else getattr(
            config, "mewtator_intro_enabled", True
        )
        if intro_enabled and mod_paths:
            intro_path = resource_path("bundled_mods", "MewtatorIntro")
            if intro_path not in mod_paths:
                mod_paths.append(intro_path)

        return mod_paths

    def get_missing_mod_names(self, mod_list: ModList) -> List[str]:
        return [mod.name for mod in mod_list.missing_mods]
    
    def find_circular_dependencies(self, mod_list: ModList) -> List[List[str]]:
        """Return groups of enabled mods that form dependency cycles...
        """
        enabled_mods = mod_list.enabled_mods
        enabled_names = {mod.name for mod in enabled_mods}
        graph: Dict[str, List[str]] = {mod.name: [] for mod in enabled_mods}

        for mod in enabled_mods:
            for req_item in mod.requirements:
                if isinstance(req_item, dict):
                    req_string = req_item.get('mod', '')
                elif isinstance(req_item, str):
                    req_string = req_item
                else:
                    continue

                parsed = parse_requirement(req_string)
                if not parsed:
                    continue

                req_mod_name, _, _ = parsed
                if req_mod_name in enabled_names:
                    graph[mod.name].append(req_mod_name)

        # Tarjan's strongly-connected-components algorithm!
        # (https://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm) - Tim
        index = 0
        indices: Dict[str, int] = {}
        lowlinks: Dict[str, int] = {}
        stack: List[str] = []
        on_stack = set()
        components: List[List[str]] = []

        def strongconnect(name: str):
            nonlocal index
            indices[name] = index
            lowlinks[name] = index
            index += 1
            stack.append(name)
            on_stack.add(name)

            for dep_name in graph[name]:
                if dep_name not in indices:
                    strongconnect(dep_name)
                    lowlinks[name] = min(lowlinks[name], lowlinks[dep_name])
                elif dep_name in on_stack:
                    lowlinks[name] = min(lowlinks[name], indices[dep_name])

            if lowlinks[name] == indices[name]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.append(member)
                    if member == name:
                        break
                components.append(component)

        for name in graph:
            if name not in indices:
                strongconnect(name)

        position = {mod.name: idx for idx, mod in enumerate(enabled_mods)}
        cycles = []
        for component in components:
            if len(component) > 1 or component[0] in graph[component[0]]:
                component.sort(key=lambda name: position[name])
                cycles.append(component)

        cycles.sort(key=lambda group: min(position[name] for name in group))
        return cycles

    def validate_requirements(
        self,
        mod_list: ModList,
        circular_dependency_template: str = None,
    ) -> List[str]:
        """
        Validate mod requirements and mark mods with unmet requirements.
        
        Returns:
            List of error messages for mods with unmet requirements.
        """

        errors = []

        # Clear stale validation state first. (A mod that was previously enabled
        # with a conflict should stop looking invalid as soon as it is disabled)... - Tim
        for mod in mod_list.all_mods:
            mod.has_unmet_requirements = False
            mod.requirement_status = None

        def mark_unmet(mod: Mod, status: str):
            mod.has_unmet_requirements = True
            # Error always wins so a missing/invalid requirement can never be
            # downgraded to yellow by a separate version mismatch... - Tim
            if status == "error" or mod.requirement_status is None:
                mod.requirement_status = status

        enabled_mods = mod_list.enabled_mods
        
        mod_positions = {mod.name: idx for idx, mod in enumerate(enabled_mods)}
        mod_versions = {mod.name: mod.version for mod in enabled_mods}

        circular_groups = self.find_circular_dependencies(mod_list)
        circular_group_by_mod = {}
        for group_index, group in enumerate(circular_groups):
            circular_message = (
                circular_dependency_template
                or "Circular dependency detected between enabled mods: {mods}. "
                   "No valid load order can satisfy these requirements."
            )
            errors.append(circular_message.format(mods=", ".join(group)))
            for mod_name in group:
                circular_group_by_mod[mod_name] = group_index
                circular_mod = mod_list.get_mod_by_name(mod_name)
                if circular_mod is not None:
                    mark_unmet(circular_mod, "error")
        
        for idx, mod in enumerate(enabled_mods):
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
                    mark_unmet(mod, "error")
                    continue
                
                req_mod_name, operator, req_version = parsed
                
                if req_mod_name not in mod_positions:
                    errors.append(f"{mod.name}: Required mod '{req_mod_name}' is not enabled")
                    mark_unmet(mod, "error")
                    continue
                
                req_position = mod_positions[req_mod_name]

                same_circular_group = (
                    mod.name in circular_group_by_mod
                    and circular_group_by_mod.get(mod.name) == circular_group_by_mod.get(req_mod_name)
                )
                if req_position > idx and not same_circular_group:
                    errors.append(f"{mod.name}: Required mod '{req_mod_name}' must be loaded before this mod (move it up in the list)")
                    mark_unmet(mod, "error")
                    continue
                
                if operator and req_version:
                    req_mod_version = mod_versions.get(req_mod_name, '')
                    if not check_requirement(req_mod_version, operator, req_version):
                        errors.append(f"{mod.name}: Required mod '{req_mod_name}' version {req_mod_version} does not satisfy {operator}{req_version}")
                        mark_unmet(mod, "warning")
        
        return errors
    
    def detect_conflicts(self, mod_list: ModList, config) -> List[str]:
        """
        Detect conflicts in savefile_suffix and inherit_save settings.
        
        TEMPORARILY DISABLED: These features are not yet functional in the game.
        
        Returns:
            List of warning messages about conflicts.
        """
        warnings = []
        # enabled_mods = mod_list.enabled_mods
        # 
        # savefile_mods = [mod for mod in enabled_mods if mod.savefile_suffix]
        # if len(savefile_mods) > 1:
        #     mod_names = [mod.name for mod in savefile_mods]
        #     if config.savefile_suffix_override:
        #         warnings.append(f"Multiple mods specify savefile_suffix: {', '.join(mod_names)}. Using settings override: '{config.savefile_suffix_override}'")
        #     else:
        #         winner = savefile_mods[-1]
        #         warnings.append(f"Multiple mods specify savefile_suffix: {', '.join(mod_names)}. Using '{winner.name}': '{winner.savefile_suffix}'")
        # 
        # inherit_mods = [mod for mod in enabled_mods if mod.inherit_save]
        # if len(inherit_mods) > 1:
        #     mod_names = [mod.name for mod in inherit_mods]
        #     if config.inherit_save_override:
        #         warnings.append(f"Multiple mods specify inherit_save: {', '.join(mod_names)}. Using settings override: '{config.inherit_save_override}'")
        #     else:
        #         winner = inherit_mods[-1]
        #         warnings.append(f"Multiple mods specify inherit_save: {', '.join(mod_names)}. Using '{winner.name}': '{winner.inherit_save}'")
        
        return warnings
    
    def auto_sort(
        self,
        mod_list: ModList,
        circular_dependency_warning: str = None,
    ) -> Tuple[List[str], List[str]]:
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
        
        # Use the same explicit graph-cycle check as launch validation... - Tim
        if self.find_circular_dependencies(mod_list):
            warnings.append(
                circular_dependency_warning
                or "Circular dependencies detected. Some requirements may not be satisfied."
            )
        
        return mod_names, warnings

