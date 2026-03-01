import os
import sys
import re
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
        # Linux / Steam Deck
        steam_paths = [
            Path.home() / ".local" / "share" / "Steam",  # Common Linux / Steam Deck default
            Path.home() / ".steam" / "steam",
            Path("~/.steam/steam").expanduser(),
            Path("/home/deck/.local/share/Steam"),  # Steam Deck specific
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
                    if '"path"' in line.lower():
                        # Extract the path value from the VDF line
                        # Format: "path"		"/some/path"
                        parts = line.split('"')
                        # Find the last quoted string which should be the path value
                        for i in range(len(parts) - 1, -1, -1):
                            part = parts[i].strip()
                            if part and (part.startswith('/') or part.startswith('\\') or (':' in part and len(part) > 2)):
                                path = os.path.normpath(part)
                                candidates.append(os.path.join(path, "steamapps", "common", "Mewgenics"))
                                break
        except Exception:
            pass
    
    for c in candidates:
        if os.path.isdir(c):
            return c
    
    return ""


def detect_steam_app_id(game_dir: str) -> str:
    """
    Detect the Steam App ID for Mewgenics by searching for appmanifest files.
    
    Returns:
        Steam App ID as a string, or empty string if not found.
    """
    if not game_dir:
        return ""
    
    try:
        game_path = Path(game_dir)
        if game_path.name == "Mewgenics" and game_path.parent.name == "common":
            steamapps_dir = game_path.parent.parent
            
            for manifest_file in steamapps_dir.glob("appmanifest_*.acf"):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        if '"Mewgenics"' in content or '"mewgenics"' in content.lower():
                            match = re.search(r'appmanifest_(\d+)\.acf', manifest_file.name)
                            if match:
                                return match.group(1)
                            
                            app_id_match = re.search(r'"appid"\s+"(\d+)"', content)
                            if app_id_match:
                                return app_id_match.group(1)
                except Exception:
                    continue
    except Exception:
        pass
    
    return ""
