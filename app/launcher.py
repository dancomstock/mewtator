import os
import sys
import subprocess
from tkinter import messagebox
from app.i18n import t


def is_proton_scenario(exe_name):
    """
    Detect if we're running a Windows .exe on Linux (Proton scenario).
    """
    return sys.platform != "win32" and exe_name.endswith(".exe")


def convert_to_proton_path(path):
    """
    Convert Linux absolute path to Proton Z: drive path.
    Example: /home/user/mods -> Z:/home/user/mods
    """
    if sys.platform != "win32":
        return f"Z:{path.replace(os.sep, '/')}"
    return path


def get_launch_options(mod_paths, game_dir=None):
    """
    Generate launch options string for Steam.
    If game_dir provided, converts paths for Proton if needed.
    Returns the command-line arguments as a string.
    """
    if not mod_paths:
        return ""
    
    # Check if we need Proton path conversion
    needs_conversion = False
    if game_dir and sys.platform != "win32":
        # Check if there's a .exe file (Proton scenario)
        potential_names = ["Mewgenics.exe"]
        for name in potential_names:
            if os.path.isfile(os.path.join(game_dir, name)):
                needs_conversion = True
                break
    
    # Convert paths if needed
    if needs_conversion:
        converted_paths = [convert_to_proton_path(p) for p in mod_paths]
    else:
        converted_paths = mod_paths
    
    # Build launch options string
    return "-modpaths " + " ".join(f'"{p}"' for p in converted_paths)


def launch_game(game_dir, mod_paths):
    """
    Launches Mewgenics with -modpaths arguments.
    mod_paths is a list of absolute mod directory paths.
    """

    # Detect executable name based on platform
    if sys.platform == "win32":
        exe_name = "Mewgenics.exe"
    else:
        # Check for various possible executable names on Linux/Mac
        potential_names = ["Mewgenics.exe", "Mewgenics", "Mewgenics.x86_64", "Mewgenics.x86"]
        exe_name = None
        for name in potential_names:
            if os.path.isfile(os.path.join(game_dir, name)):
                exe_name = name
                break
        if not exe_name:
            exe_name = "Mewgenics"  # default fallback
    
    exe = os.path.join(game_dir, exe_name)
    if not os.path.isfile(exe):
        messagebox.showerror(t("messages.launch_error"), t("messages.exe_not_found"))
        return

    # Check if running Windows .exe on Linux (Proton scenario)
    if is_proton_scenario(exe_name):
        # Check if mods are outside game directory
        mods_outside_game = any(not p.startswith(game_dir) for p in mod_paths)
        
        if mods_outside_game:
            result = messagebox.askyesno(
                t("messages.proton_warning_title", "Proton/Steam Deck Warning"),
                t("messages.proton_warning_text", 
                  "You are running on Linux with a Windows .exe (Proton).\n\n"
                  "Mods outside the game directory may not work correctly.\n"
                  "It's recommended to keep mods in the game folder on Linux/Steam Deck.\n\n"
                  "Continue anyway?")
            )
            if not result:
                return
        
        # Convert paths to Proton format
        mod_paths = [convert_to_proton_path(p) for p in mod_paths]

    # Build launch arguments
    args = [exe]

    # Add mod paths
    if mod_paths:
        args.append("-modpaths")
        for p in mod_paths:
            args.append(p)

    try:
        subprocess.Popen(args, cwd=game_dir)
    except Exception as e:
        messagebox.showerror(t("messages.launch_error"), t("messages.launch_failed", default="").replace("{error}", str(e)))
