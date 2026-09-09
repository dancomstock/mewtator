import tkinter as tk
from typing import Dict, Tuple

from app.utils.resource_utils import resource_path

class IconSet:
    """Loads bundled Font Awesome PNGs and keeps Tk references alive..."""

    def __init__(self, root: tk.Misc):
        self.root = root
        self._images: Dict[Tuple[str, str], tk.PhotoImage] = {}

    def get(self, name: str, theme_name: str) -> tk.PhotoImage:
        theme = "dark"
        key = (theme, name)

        if key not in self._images:
            self._images[key] = tk.PhotoImage(
                master=self.root,
                file=resource_path(
                    "assets",
                    "icons",
                    "fontawesome",
                    theme,
                    f"{name}.png",
                ),
            )

        return self._images[key]

    def brand(self) -> tk.PhotoImage:
        key = ("brand", "mewtator")

        if key not in self._images:
            self._images[key] = tk.PhotoImage(
                master=self.root,
                file=resource_path("assets", "icons", "mewtator-64.png"),
            )

        return self._images[key]