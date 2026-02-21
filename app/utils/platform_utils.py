import os
import sys
from app.core.strategies.platform_strategy import PlatformFactory


def get_executable_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_file_or_folder(path: str):
    platform = PlatformFactory.create()
    platform.open_path(path)
