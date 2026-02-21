from abc import ABC, abstractmethod
from typing import List
import sys
import os
import subprocess


class PlatformStrategy(ABC):
    @abstractmethod
    def open_path(self, path: str):
        pass
    
    @abstractmethod
    def get_executable_names(self) -> List[str]:
        pass
    
    @abstractmethod
    def normalize_path(self, path: str) -> str:
        pass


class WindowsPlatform(PlatformStrategy):
    def open_path(self, path: str):
        os.startfile(path)
    
    def get_executable_names(self) -> List[str]:
        return ["Mewgenics.exe"]
    
    def normalize_path(self, path: str) -> str:
        return os.path.normpath(path)


class LinuxPlatform(PlatformStrategy):
    def open_path(self, path: str):
        subprocess.Popen(["xdg-open", path])
    
    def get_executable_names(self) -> List[str]:
        return ["Mewgenics.exe", "Mewgenics", "Mewgenics.x86_64", "Mewgenics.x86"]
    
    def normalize_path(self, path: str) -> str:
        return os.path.normpath(path)


class MacPlatform(PlatformStrategy):
    def open_path(self, path: str):
        subprocess.Popen(["open", path])
    
    def get_executable_names(self) -> List[str]:
        return ["Mewgenics", "Mewgenics.app"]
    
    def normalize_path(self, path: str) -> str:
        return os.path.normpath(path)


class PlatformFactory:
    @staticmethod
    def create() -> PlatformStrategy:
        if sys.platform == "win32":
            return WindowsPlatform()
        elif sys.platform == "darwin":
            return MacPlatform()
        else:
            return LinuxPlatform()
