import tkinter as tk
import sys
from contextlib import contextmanager

import sv_ttk

try:
    import pywinstyles
except Exception:
    pywinstyles = None


class ThemeService:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current_theme = "dark"
        self.available_themes = ["light", "dark"]
    
    def get_available_themes(self):
        return self.available_themes

    def normalize_theme_name(self, theme_name: str) -> str:
        if not theme_name:
            return "dark"

        name = theme_name.strip().lower()
        aliases = {
            "sun-valley-dark": "dark",
            "sun-valley-light": "light",
            "default": "dark"
        }
        normalized = aliases.get(name, name)
        if normalized not in self.available_themes:
            return "dark"
        return normalized

    def _apply_titlebar_theme(self, window: tk.Misc):
        if sys.platform != "win32" or pywinstyles is None:
            return

        try:
            version = sys.getwindowsversion()
            is_dark = self.current_theme == "dark"

            if version.major == 10 and version.build >= 22000:
                pywinstyles.change_header_color(window, "#1c1c1c" if is_dark else "#fafafa")
                pywinstyles.change_title_color(window, "#ffffff" if is_dark else "#000000")
            elif version.major == 10:
                pywinstyles.apply_style(window, "dark" if is_dark else "normal")
                window.wm_attributes("-alpha", 0.99)
                window.wm_attributes("-alpha", 1)
        except Exception:
            pass
    
    def set_theme(self, theme_name: str):
        normalized = self.normalize_theme_name(theme_name)
        self.current_theme = normalized
        try:
            sv_ttk.set_theme(normalized)
        except Exception:
            pass

        self._apply_titlebar_theme(self.root)
    
    def get_current_theme(self):
        return self.current_theme

    def bind_root(self, root: tk.Tk):
        self.root = root
        self._apply_titlebar_theme(self.root)

    def apply_titlebar(self, window: tk.Misc, theme_name: str):
        self.current_theme = self.normalize_theme_name(theme_name)
        self._apply_titlebar_theme(window)

    def get_color_scheme(self, theme_name: str) -> dict:
        normalized = self.normalize_theme_name(theme_name)
        if normalized == "dark":
            return {
                "bg": "#1e1e1e",
                "fg": "#e6e6e6",
                "select_bg": "#2e62b8",
                "select_fg": "#ffffff",
                "text_bg": "#1c1c1c",
                "text_fg": "#e6e6e6",
                "menu_bg": "#2b2b2b",
                "menu_fg": "#ffffff",
                "menu_active_bg": "#3a3a3a",
                "menu_active_fg": "#ffffff"
            }
        return {
            "bg": "#f0f0f0",
            "fg": "#111111",
            "select_bg": "#2e62b8",
            "select_fg": "#ffffff",
            "text_bg": "#ffffff",
            "text_fg": "#111111",
            "menu_bg": "#f0f0f0",
            "menu_fg": "#000000",
            "menu_active_bg": "#e0e0e0",
            "menu_active_fg": "#000000"
        }
    
    @contextmanager
    def file_dialog_safe_theme(self):
        """
        Context manager that temporarily switches to light theme on Linux
        when in dark mode to fix file dialog text visibility issues.
        
        Usage:
            with theme_service.file_dialog_safe_theme():
                filepath = filedialog.askopenfilename(...)
        """
        needs_workaround = sys.platform.startswith('linux') and self.current_theme == 'dark'
        
        if needs_workaround:
            sv_ttk.set_theme('light')
        
        try:
            yield
        finally:
            if needs_workaround:
                sv_ttk.set_theme('dark')
