import os
import shlex
from typing import List
from app.core.strategies.platform_strategy import PlatformFactory
from app.core.strategies.launch_strategy import LaunchStrategyFactory
from app.core.strategies.path_strategy import PathStrategyFactory
from app.utils.logging_utils import get_logger


class GameLauncherService:
    def __init__(self):
        self.platform = PlatformFactory.create()
    
    def find_executable(self, game_dir: str) -> str:
        exe_names = self.platform.get_executable_names()
        
        for name in exe_names:
            exe_path = os.path.join(game_dir, name)
            if os.path.isfile(exe_path):
                return exe_path
        
        return os.path.join(game_dir, exe_names[0])
    
    def _build_extra_args(self, config, mod_list) -> List[str]:
        """Build extra launch arguments from config and mod list."""
        extra_args = []
        
        if not config:
            return extra_args
        
        if config.custom_launch_options:
            try:
                custom_args = shlex.split(config.custom_launch_options)
                extra_args.extend(custom_args)
            except ValueError:
                extra_args.extend(config.custom_launch_options.split())
        
        if config.dev_mode_enabled:
            extra_args.extend(["-dev_mode", "true"])
        
        if config.debug_console_enabled:
            extra_args.extend(["-enable_debugconsole", "true"])
        
        savefile_suffix = config.savefile_suffix_override
        if not savefile_suffix and mod_list:
            enabled_mods = mod_list.enabled_mods
            mod_iter = enabled_mods if config.use_original_load_order else reversed(enabled_mods)
            for mod in mod_iter:
                if mod.savefile_suffix:
                    savefile_suffix = mod.savefile_suffix
                    break
        if savefile_suffix:
            extra_args.extend(["-savefile_suffix", savefile_suffix])
        
        inherit_save = config.inherit_save_override
        if not inherit_save and mod_list:
            enabled_mods = mod_list.enabled_mods
            mod_iter = enabled_mods if config.use_original_load_order else reversed(enabled_mods)
            for mod in mod_iter:
                if mod.inherit_save:
                    inherit_save = mod.inherit_save
                    break
        if inherit_save:
            extra_args.extend(["-inherit_save", inherit_save])
        
        return extra_args
    
    def _apply_load_order(self, mod_paths: List[str], config) -> List[str]:
        """Apply load order logic to mod paths."""
        if config and config.use_original_load_order:
            return mod_paths
        else:
            return list(reversed(mod_paths))
    
    def launch_game(self, game_dir: str, mod_paths: List[str], config=None, mod_list=None):
        exe_path = self.find_executable(game_dir)
        
        if not os.path.isfile(exe_path):
            raise FileNotFoundError(f"Game executable not found: {exe_path}")
        
        launch_strategy = LaunchStrategyFactory.create(game_dir)
        path_strategy = PathStrategyFactory.create(game_dir)
        
        extra_args = self._build_extra_args(config, mod_list)
        final_paths = self._apply_load_order(mod_paths, config)
        converted_paths = path_strategy.convert_mod_paths(final_paths, game_dir)
        
        logger = get_logger()
        logger.info("Launch executable: %s", exe_path)
        for arg in extra_args:
            logger.info("Launch extra arg: %s", arg)
        for path in converted_paths:
            logger.info("Launch mod path: %s", path)
        
        launch_strategy.launch(exe_path, converted_paths, game_dir, extra_args)
    
    def get_launch_options(self, game_dir: str, mod_paths: List[str], config=None, mod_list=None) -> str:
        launch_strategy = LaunchStrategyFactory.create(game_dir)
        path_strategy = PathStrategyFactory.create(game_dir)
        
        extra_args = self._build_extra_args(config, mod_list)
        final_paths = self._apply_load_order(mod_paths, config)
        converted_paths = path_strategy.convert_mod_paths(final_paths, game_dir)
        
        return launch_strategy.get_launch_options(converted_paths, extra_args)
    
    def export_bat_file(self, game_dir: str, mod_paths: List[str], output_path: str, config=None, mod_list=None) -> str:
        """
        Export launch options to a .bat file.
        
        Args:
            game_dir: Game installation directory
            mod_paths: List of mod paths
            output_path: Path where to save the .bat file
            config: Config object with launch options
            mod_list: ModList object
            
        Returns:
            Steam launch option string to use with the .bat file
        """
        exe_path = self.find_executable(game_dir)
        path_strategy = PathStrategyFactory.create(game_dir)
        
        extra_args = self._build_extra_args(config, mod_list)
        final_paths = self._apply_load_order(mod_paths, config)
        converted_paths = path_strategy.convert_mod_paths(final_paths, game_dir)
        
        cmd_parts = [f'start "" "{exe_path}"']
        cmd_parts.extend(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in extra_args)
        
        if converted_paths:
            cmd_parts.append("-modpaths")
            cmd_parts.extend(f'"{path}"' for path in converted_paths)
        
        bat_content = "@echo off\n"
        bat_content += "REM Mewtator Auto-Generated Launch Script\n"
        bat_content += "REM This script launches Mewgenics with mods\n\n"
        bat_content += " ".join(cmd_parts) + "\n"
        bat_content += "exit\n"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        return f'"{output_path}" %command%'
    
    def should_warn_external_mods(self, game_dir: str, mod_paths: List[str]) -> bool:
        path_strategy = PathStrategyFactory.create(game_dir)
        return path_strategy.should_warn_about_external_mods(mod_paths, game_dir)
