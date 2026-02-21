from typing import List, Optional, Callable
from app.core.models.mod import Mod


class ModList:
    def __init__(self, mods: Optional[List[Mod]] = None):
        self._mods: List[Mod] = mods or []
        self._observers: List[Callable] = []
    
    def add_observer(self, callback: Callable):
        self._observers.append(callback)
    
    def _notify_observers(self):
        for callback in self._observers:
            callback()
    
    @property
    def all_mods(self) -> List[Mod]:
        return self._mods.copy()
    
    @property
    def enabled_mods(self) -> List[Mod]:
        return [mod for mod in self._mods if mod.enabled and not mod.missing]
    
    @property
    def disabled_mods(self) -> List[Mod]:
        return [mod for mod in self._mods if not mod.enabled]
    
    @property
    def missing_mods(self) -> List[Mod]:
        return [mod for mod in self._mods if mod.enabled and mod.missing]
    
    @property
    def enabled_mod_names(self) -> List[str]:
        return [mod.name for mod in self._mods if mod.enabled]
    
    def get_mod_by_name(self, name: str) -> Optional[Mod]:
        for mod in self._mods:
            if mod.name == name:
                return mod
        return None
    
    def enable_mod(self, mod_name: str):
        mod = self.get_mod_by_name(mod_name)
        if mod and not mod.enabled:
            mod.enabled = True
            self._notify_observers()
    
    def disable_mod(self, mod_name: str):
        mod = self.get_mod_by_name(mod_name)
        if mod and mod.enabled:
            mod.enabled = False
            self._notify_observers()
    
    def enable_all(self):
        for mod in self._mods:
            if not mod.missing:
                mod.enabled = True
        self._notify_observers()
    
    def disable_all(self):
        for mod in self._mods:
            mod.enabled = False
        self._notify_observers()
    
    def move_up(self, mod_name: str):
        enabled = [m for m in self._mods if m.enabled]
        index = next((i for i, m in enumerate(enabled) if m.name == mod_name), None)
        
        if index is not None and index > 0:
            all_mods = self._mods.copy()
            
            old_idx = all_mods.index(enabled[index])
            target_idx = all_mods.index(enabled[index - 1])
            
            all_mods[old_idx], all_mods[target_idx] = all_mods[target_idx], all_mods[old_idx]
            self._mods = all_mods
            self._notify_observers()
    
    def move_down(self, mod_name: str):
        enabled = [m for m in self._mods if m.enabled]
        index = next((i for i, m in enumerate(enabled) if m.name == mod_name), None)
        
        if index is not None and index < len(enabled) - 1:
            all_mods = self._mods.copy()
            
            old_idx = all_mods.index(enabled[index])
            target_idx = all_mods.index(enabled[index + 1])
            
            all_mods[old_idx], all_mods[target_idx] = all_mods[target_idx], all_mods[old_idx]
            self._mods = all_mods
            self._notify_observers()
    
    def move_to_top(self, mod_name: str):
        mod = self.get_mod_by_name(mod_name)
        if mod and mod.enabled:
            self._mods.remove(mod)
            
            first_enabled_idx = next((i for i, m in enumerate(self._mods) if m.enabled), len(self._mods))
            self._mods.insert(first_enabled_idx, mod)
            self._notify_observers()
    
    def move_to_bottom(self, mod_name: str):
        mod = self.get_mod_by_name(mod_name)
        if mod and mod.enabled:
            self._mods.remove(mod)
            
            last_enabled_idx = next((i for i in range(len(self._mods) - 1, -1, -1) if self._mods[i].enabled), -1)
            self._mods.insert(last_enabled_idx + 1, mod)
            self._notify_observers()
    
    def set_order(self, enabled_names: List[str]):
        enabled_map = {mod.name: mod for mod in self._mods if mod.enabled}
        disabled_mods = [mod for mod in self._mods if not mod.enabled]
        
        new_enabled = []
        for name in enabled_names:
            if name in enabled_map:
                new_enabled.append(enabled_map[name])
        
        for mod in enabled_map.values():
            if mod not in new_enabled:
                new_enabled.append(mod)
        
        self._mods = new_enabled + disabled_mods
        self._notify_observers()
    
    def replace_mods(self, mods: List[Mod]):
        self._mods = mods
        self._notify_observers()
