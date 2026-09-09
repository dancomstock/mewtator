import os
import sys
from pathlib import Path

from app.core.strategies.platform_strategy import PlatformFactory

def get_executable_dir() -> str:
    """Return the directory that owns Mewtator's writable app files...
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return str(Path(__file__).resolve().parents[2])

def open_file_or_folder(path: str):
    platform = PlatformFactory.create()
    platform.open_path(path)
