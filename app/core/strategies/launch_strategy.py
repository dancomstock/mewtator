from abc import ABC, abstractmethod
from typing import List
import os
import subprocess


class LaunchStrategy(ABC):
    @abstractmethod
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        pass
    
    @abstractmethod
    def get_launch_options(self, mod_paths: List[str], extra_args: List[str] = None) -> str:
        pass


class DirectLaunchStrategy(LaunchStrategy):
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        args = [executable_path]
        
        if extra_args:
            args.extend(extra_args)
        
        if mod_paths:
            args.append("-modpaths")
            args.extend(mod_paths)
        
        subprocess.Popen(args, cwd=game_dir)
    
    def get_launch_options(self, mod_paths: List[str], extra_args: List[str] = None) -> str:
        parts = []
        
        if extra_args:
            parts.extend(extra_args)
        
        if mod_paths:
            parts.append("-modpaths")
            parts.extend(f'"{p}"' for p in mod_paths)
        
        return " ".join(parts)


class ProtonLaunchStrategy(LaunchStrategy):
    def __init__(self, path_converter):
        self.path_converter = path_converter
    
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        converted_paths = [self.path_converter(p) for p in mod_paths]
        
        args = [executable_path]
        
        if extra_args:
            args.extend(extra_args)
        
        if converted_paths:
            args.append("-modpaths")
            args.extend(converted_paths)
        
        subprocess.Popen(args, cwd=game_dir)
    
    def get_launch_options(self, mod_paths: List[str], extra_args: List[str] = None) -> str:
        parts = []
        
        if extra_args:
            parts.extend(extra_args)
        
        if mod_paths:
            converted_paths = [self.path_converter(p) for p in mod_paths]
            parts.append("-modpaths")
            parts.extend(f'"{p}"' for p in converted_paths)
        
        return " ".join(parts)


class LaunchStrategyFactory:
    @staticmethod
    def create(game_dir: str) -> LaunchStrategy:
        from app.core.strategies.path_strategy import PathStrategyFactory, ProtonPathStrategy
        
        path_strategy = PathStrategyFactory.create(game_dir)
        
        if isinstance(path_strategy, ProtonPathStrategy):
            return ProtonLaunchStrategy(ProtonPathStrategy._convert_to_proton_path)
        
        return DirectLaunchStrategy()
