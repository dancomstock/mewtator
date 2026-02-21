import os
import sys
from pathlib import Path


def auto_detect_game_install() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Valve\Steam"
            )
            steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
            key.Close()
            
            return _check_steam_libraries(steam_path)
        except Exception:
            pass
    
    elif sys.platform == "darwin":
        steam_paths = [
            Path.home() / "Library" / "Application Support" / "Steam",
            Path("~/.steam/steam").expanduser(),
        ]
        
        for steam_path in steam_paths:
            if steam_path.exists():
                result = _check_steam_libraries(str(steam_path))
                if result:
                    return result
    
    else:
        steam_paths = [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path("~/.steam/steam").expanduser(),
        ]
        
        for steam_path in steam_paths:
            if steam_path.exists():
                result = _check_steam_libraries(str(steam_path))
                if result:
                    return result
    
    return ""


def _check_steam_libraries(steam_path: str) -> str:
    candidates = [
        os.path.join(steam_path, "steamapps", "common", "Mewgenics"),
    ]
    
    lib_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(lib_vdf):
        try:
            with open(lib_vdf, "r", encoding="utf-8") as f:
                for line in f:
                    if '"path"' in line.lower() and ":" in line:
                        parts = line.split('"')
                        if len(parts) >= 4:
                            path = os.path.normpath(parts[3])
                            candidates.append(os.path.join(path, "steamapps", "common", "Mewgenics"))
        except Exception:
            pass
    
    for c in candidates:
        if os.path.isdir(c):
            return c
    
    return ""
