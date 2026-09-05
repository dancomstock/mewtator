import ctypes
import ctypes.util
import os
import sys
from pathlib import Path
from typing import Optional

def resource_path(*parts: str) -> str:
    """Return an absolute path for source and PyInstaller builds..."""

    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[2]
    return str(base_path.joinpath(*parts))


def register_private_font(font_path: str) -> bool:
    """Register a bundled font for this process without installing it globally..."""

    if not os.path.isfile(font_path):
        return False

    try:
        if sys.platform == "win32":
            # FR_PRIVATE keeps the font scoped to Mewtator...
            return bool(ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0))

        if sys.platform.startswith("linux"):
            library_name = ctypes.util.find_library("fontconfig")
            if not library_name:
                return False
            fontconfig = ctypes.CDLL(library_name)
            fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
            fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
            config = fontconfig.FcConfigGetCurrent()
            added = bool(fontconfig.FcConfigAppFontAddFile(config, os.fsencode(font_path)))
            if added:
                fontconfig.FcConfigBuildFonts.argtypes = [ctypes.c_void_p]
                fontconfig.FcConfigBuildFonts.restype = ctypes.c_int
                fontconfig.FcConfigBuildFonts(config)
            return added
    except Exception:
        return False

    # (Tk will use fallback)... - Tim
    return False


def apply_app_icon(window) -> Optional[object]:
    """Apply the bundled icon and retain its Tk image reference..."""

    png_path = resource_path("assets", "icons", "mewtator.png")
    ico_path = resource_path("assets", "icons", "mewtator.ico")
    image = None

    try:
        import tkinter as tk

        if os.path.isfile(png_path):
            image = tk.PhotoImage(file=png_path)
            window.iconphoto(True, image)
            window._mewtator_icon = image
    except Exception:
        pass

    if sys.platform == "win32" and os.path.isfile(ico_path):
        try:
            window.iconbitmap(ico_path)
        except Exception:
            pass

    return image