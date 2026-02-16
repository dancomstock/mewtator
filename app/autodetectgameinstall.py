import os
import sys
from pathlib import Path

def auto_detect_game_install():
    """
    Auto-detect Mewgenics install location across different platforms.
    Returns the game directory path or empty string if not found.
    """
    
    if sys.platform == "win32":
        # Windows: Try Steam registry
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
        # macOS: Check common Steam locations
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
        # Linux: Check common Steam locations
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
    
    return ""  # fallback


def _check_steam_libraries(steam_path):
    """
    Check Steam library folders for Mewgenics installation.
    Works cross-platform.
    """
    candidates = [
        os.path.join(steam_path, "steamapps", "common", "Mewgenics"),
    ]
    
    # Also check libraryfolders.vdf for extra libraries
    lib_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(lib_vdf):
        try:
            with open(lib_vdf, "r", encoding="utf-8") as f:
                for line in f:
                    if '"path"' in line.lower() and ":" in line:
                        # Parse VDF format: "path" "C:\\Steam\\Library"
                        parts = line.split('"')
                        if len(parts) >= 4:
                            # Normalize path for cross-platform compatibility
                            path = os.path.normpath(parts[3])
                            candidates.append(os.path.join(path, "steamapps", "common", "Mewgenics"))
        except Exception:
            pass
    
    # Check each candidate
    for c in candidates:
        if os.path.isdir(c):
            return c
    
    return ""
