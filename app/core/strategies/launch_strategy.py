from abc import ABC, abstractmethod
from typing import List
import os
import subprocess


class LaunchStrategy(ABC):
    @abstractmethod
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str):
        pass
    
    @abstractmethod
    def get_launch_options(self, mod_paths: List[str]) -> str:
        pass


class DirectLaunchStrategy(LaunchStrategy):
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str):
        args = [executable_path]
        if mod_paths:
            args.append("-modpaths")
            args.extend(mod_paths)
        
        subprocess.Popen(args, cwd=game_dir)
    
    def get_launch_options(self, mod_paths: List[str]) -> str:
        if not mod_paths:
            return ""
        return "-modpaths " + " ".join(f'"{p}"' for p in mod_paths)


class ProtonLaunchStrategy(LaunchStrategy):
    def __init__(self, path_converter):
        self.path_converter = path_converter
    
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str):
        converted_paths = [self.path_converter(p) for p in mod_paths]
        
        args = [executable_path]
        if converted_paths:
            args.append("-modpaths")
            args.extend(converted_paths)
        
        subprocess.Popen(args, cwd=game_dir)
    
    def get_launch_options(self, mod_paths: List[str]) -> str:
        if not mod_paths:
            return ""
        converted_paths = [self.path_converter(p) for p in mod_paths]
        return "-modpaths " + " ".join(f'"{p}"' for p in converted_paths)


class LaunchStrategyFactory:
    @staticmethod
    def create(game_dir: str) -> LaunchStrategy:
        from app.core.strategies.path_strategy import PathStrategyFactory, ProtonPathStrategy
        
        path_strategy = PathStrategyFactory.create(game_dir)
        
        if isinstance(path_strategy, ProtonPathStrategy):
            return ProtonLaunchStrategy(ProtonPathStrategy._convert_to_proton_path)
        
        return DirectLaunchStrategy()
