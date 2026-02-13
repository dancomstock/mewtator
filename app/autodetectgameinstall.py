import winreg
import os

def auto_detect_game_install():
    # Try Steam registry
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam"
        )
        steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
        key.Close()

        # Check common Steam library locations
        candidates = [
            os.path.join(steam_path, "steamapps", "common", "Mewgenics"),
        ]

        # Also check libraryfolders.vdf for extra libraries
        lib_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if os.path.exists(lib_vdf):
            with open(lib_vdf, "r", encoding="utf-8") as f:
                for line in f:
                    if '"' in line and ":" in line:
                        path = line.split('"')[3]
                        candidates.append(os.path.join(path, "steamapps", "common", "Mewgenics"))

        for c in candidates:
            if os.path.isdir(c):
                return c

    except Exception:
        pass

    return ""  # fallback
