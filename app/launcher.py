import os
import subprocess
from tkinter import messagebox
from app.i18n import t

def launch_game(game_dir, mod_paths):
    """
    Launches Mewgenics with -modpaths arguments.
    mod_paths is a list of absolute mod directory paths.
    """

    exe = os.path.join(game_dir, "Mewgenics.exe")
    if not os.path.isfile(exe):
        messagebox.showerror(t("messages.launch_error"), t("messages.exe_not_found"))
        return

    # Build launch arguments
    args = [exe]

    # Add mod count
    # args.append("-modcount")
    # args.append(str(len(mod_paths)))

    # Add mod paths
    if mod_paths:
        args.append("-modpaths")
        for p in mod_paths:
            args.append(p)

    try:
        subprocess.Popen(args, cwd=game_dir)
    except Exception as e:
        messagebox.showerror(t("messages.launch_error"), t("messages.launch_failed", default="").replace("{error}", str(e)))
