from abc import ABC, abstractmethod
from typing import List
import os
import sys


class PathStrategy(ABC):
    @abstractmethod
    def convert_mod_paths(self, paths: List[str], game_dir: str) -> List[str]:
        pass
    
    @abstractmethod
    def should_warn_about_external_mods(self, mod_paths: List[str], game_dir: str) -> bool:
        pass


class NativePathStrategy(PathStrategy):
    def convert_mod_paths(self, paths: List[str], game_dir: str) -> List[str]:
        return paths
    
    def should_warn_about_external_mods(self, mod_paths: List[str], game_dir: str) -> bool:
        return False


class ProtonPathStrategy(PathStrategy):
    def convert_mod_paths(self, paths: List[str], game_dir: str) -> List[str]:
        return [self._convert_to_proton_path(p) for p in paths]
    
    def should_warn_about_external_mods(self, mod_paths: List[str], game_dir: str) -> bool:
        return any(not p.startswith(game_dir) for p in mod_paths)
    
    @staticmethod
    def _convert_to_proton_path(path: str) -> str:
        return f"Z:{path.replace(os.sep, '/')}"


class PathStrategyFactory:
    @staticmethod
    def create(game_dir: str) -> PathStrategy:
        if sys.platform == "win32":
            return NativePathStrategy()
        
        potential_exe_names = ["Mewgenics.exe"]
        for name in potential_exe_names:
            if os.path.isfile(os.path.join(game_dir, name)):
                return ProtonPathStrategy()
        
        return NativePathStrategy()
