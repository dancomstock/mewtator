from abc import ABC, abstractmethod
from typing import List
import os
import sys
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
    def __init__(self, path_converter, game_dir: str):
        self.path_converter = path_converter
        self.game_dir = game_dir
        self.app_id = self._detect_steam_app_id()
    
    def _detect_steam_app_id(self) -> str:
        """Detect Steam App ID for the game."""
        from app.utils.game_detector import detect_steam_app_id
        return detect_steam_app_id(self.game_dir)
    
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        # On Linux, we need to launch through Steam instead of running the .exe directly
        if sys.platform.startswith('linux'):
            self._launch_via_steam(executable_path, mod_paths, game_dir, extra_args)
        else:
            # Fallback to direct launch on other platforms
            self._launch_direct(executable_path, mod_paths, game_dir, extra_args)
    
    def _launch_via_steam(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        """Launch the game through Steam on Linux."""
        if not self.app_id:
            raise RuntimeError(
                "Could not detect Steam App ID. Please ensure the game is installed through Steam.\n\n"
                "To launch with mods on Linux, you need to:\n"
                "1. Use 'Copy Launch Options' from the File menu\n"
                "2. Paste them in Steam: Right-click Mewgenics → Properties → Launch Options\n"
                ""
                "3. Launch the game from Steam"
            )
        
        # Build the launch options that Steam should pass to the game
        launch_options = []
        
        if extra_args:
            launch_options.extend(extra_args)
        
        if mod_paths:
            converted_paths = [self.path_converter(p) for p in mod_paths]
            launch_options.append("-modpaths")
            launch_options.extend(converted_paths)
        
        # Try to launch via Steam command with arguments
        # Note: Steam may not pass these arguments unless they're also set in Steam's Launch Options
        try:
            # Try steam command first
            cmd = ['steam', '-applaunch', self.app_id]
            if launch_options:
                cmd.extend(launch_options)
            subprocess.Popen(cmd, start_new_session=True)
        except FileNotFoundError:
            try:
                # Fallback to xdg-open with steam:// protocol
                steam_uri = f"steam://rungameid/{self.app_id}"
                subprocess.Popen(['xdg-open', steam_uri], start_new_session=True)
            except FileNotFoundError:
                raise RuntimeError(
                    "Could not launch Steam. Please ensure Steam is installed and running.\n\n"
                    f"You can manually launch with: steam -applaunch {self.app_id}"
                )
    
    def _launch_direct(self, executable_path: str, mod_paths: List[str], game_dir: str, extra_args: List[str] = None):
        """Direct launch (fallback for non-Linux platforms)."""
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
            return ProtonLaunchStrategy(ProtonPathStrategy._convert_to_proton_path, game_dir)
        
        return DirectLaunchStrategy()
