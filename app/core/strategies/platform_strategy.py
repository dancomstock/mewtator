from abc import ABC, abstractmethod
from typing import List
import sys
import os
import shutil
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
    @staticmethod
    def _external_process_env():
        """Return environment for launching host desktop tools..."""
        env = os.environ.copy()

        # PyInstaller modifies LD_LIBRARY_PATH so the frozen application prefers
        # bundled shared libraries. xdg-open/gio should not inherit that modified path, 
        # because they may load incompatible bundled libraries instead of system libraries... - Tim
        if getattr(sys, "frozen", False):
            original = env.get("LD_LIBRARY_PATH_ORIG")
            if original is not None:
                env["LD_LIBRARY_PATH"] = original
            else:
                env.pop("LD_LIBRARY_PATH", None)

        return env

    def open_path(self, path: str):
        target = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(target):
            raise FileNotFoundError(f"Path does not exist: {target}")

        # xdg-open is modern standard, but gio is a useful fallback on
        # desktops where xdg-open is unavailable or helper chain fails... - Tim
        commands = (
            ("xdg-open", [target]),
            ("gio", ["open", target]),
        )

        env = self._external_process_env()
        attempted = []

        for executable, args in commands:
            opener = shutil.which(executable, path=env.get("PATH"))
            if not opener:
                continue

            command = [opener, *args]
            attempted.append(executable)

            try:
                process = subprocess.Popen(
                    command,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except OSError:
                continue

            # If implementation remains alive, handoff is underway...
            try:
                return_code = process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                return

            if return_code == 0:
                return

        if attempted:
            raise RuntimeError(
                "Could not open the path with " + " or ".join(attempted)
            )
        raise RuntimeError(
            "No supported desktop opener was found (expected xdg-open or gio)"
        )

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
