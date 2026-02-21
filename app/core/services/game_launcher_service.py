import os
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
    
    def launch_game(self, game_dir: str, mod_paths: List[str]):
        exe_path = self.find_executable(game_dir)
        
        if not os.path.isfile(exe_path):
            raise FileNotFoundError(f"Game executable not found: {exe_path}")
        
        launch_strategy = LaunchStrategyFactory.create(game_dir)
        path_strategy = PathStrategyFactory.create(game_dir)
        
        reversed_paths = list(reversed(mod_paths))
        converted_paths = path_strategy.convert_mod_paths(reversed_paths, game_dir)
        logger = get_logger()
        logger.info("Launch executable: %s", exe_path)
        for path in converted_paths:
            logger.info("Launch mod path: %s", path)
        launch_strategy.launch(exe_path, converted_paths, game_dir)
    
    def get_launch_options(self, game_dir: str, mod_paths: List[str]) -> str:
        launch_strategy = LaunchStrategyFactory.create(game_dir)
        path_strategy = PathStrategyFactory.create(game_dir)
        
        reversed_paths = list(reversed(mod_paths))
        converted_paths = path_strategy.convert_mod_paths(reversed_paths, game_dir)
        return launch_strategy.get_launch_options(converted_paths)
    
    def should_warn_external_mods(self, game_dir: str, mod_paths: List[str]) -> bool:
        path_strategy = PathStrategyFactory.create(game_dir)
        return path_strategy.should_warn_about_external_mods(mod_paths, game_dir)
