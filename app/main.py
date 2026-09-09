import os
import traceback
from pathlib import Path
import tkinter as tk
from app.ui.components.dialog_text import dialog_label

from app.infrastructure.config_repository import ConfigRepository
from app.infrastructure.mod_repository import ModRepository
from app.infrastructure.translation_repository import TranslationRepository
from app.core.services.config_service import ConfigService
from app.core.services.mod_service import ModService
from app.core.services.game_launcher_service import GameLauncherService
from app.core.services.dll_injection_service import DllInjectionService
from app.core.services.translation_service import TranslationService
from app.core.services.pack_service import PackService
from app.core.services.modlist_io_service import ModListIOService
from app.core.services.theme_service import ThemeService
from app.ui.controllers.main_controller import MainController
from app.ui.windows.settings_window import SettingsWindow
from app.utils.resource_utils import apply_app_icon
from app.ui.layout_utils import fit_combobox_to_values, fit_window_to_content
from app.utils.platform_utils import get_executable_dir
from app.version import versioned_title


def show_language_selection_dialog(root, translation_service, theme_service, theme_name: str):
    from tkinter import Toplevel, StringVar
    from tkinter import ttk
    
    win = Toplevel(root)
    win.withdraw()
    win.title(translation_service.get("window.dont_panic", "Don't Panic"))
    win.resizable(False, False)

    if root.state() != "withdrawn":
        win.transient(root)

    win.grab_set()
    
    def on_closing():
        pass
    win.protocol("WM_DELETE_WINDOW", on_closing)
    
    result = [None]

    colors = theme_service.get_color_scheme(theme_name)
    win.configure(bg=colors["bg"])
    theme_service.apply_titlebar(win, theme_name)

    dialog_label(
        win,
        colors,
        text=translation_service.get("settings.select_language_title", "Select Language"),
        font="MewtatorHeading",
    ).pack(pady=15)
    dialog_label(
        win,
        colors,
        text=translation_service.get("settings.select_language_text", "Choose your preferred language:"),
        font="MewtatorBody",
    ).pack(pady=5)
    
    available_langs = translation_service.get_available_languages()
    if not available_langs:
        available_langs = ["English"]
    
    lang_var = StringVar(value=available_langs[0])
    
    lang_menu = ttk.Combobox(
        win,
        textvariable=lang_var,
        values=available_langs,
        state="readonly",
        height=15,
        cursor="hand2",
    )

    fit_combobox_to_values(lang_menu, available_langs, min_chars=20)
    lang_menu.pack(pady=10)
    
    def confirm():
        result[0] = lang_var.get()
        win.destroy()
    
    confirm_btn = ttk.Button(
        win,
        text=translation_service.get("settings.confirm", "Confirm"),
        command=confirm,
        style="Primary.TButton",
        cursor="hand2",
    )
    
    confirm_btn.pack(pady=15)
    
    win.bind("<Return>", lambda e: confirm())
    win.bind("<KP_Enter>", lambda e: confirm())
    
    fit_window_to_content(
        win,
        root,
        min_width=440,
        min_height=260,
        preferred_width=440,
        preferred_height=260,
        screen_margin_x=40,
        screen_margin_y=80,
    )

    lang_menu.focus_set()
    win.deiconify()
    win.lift()
    win.focus_force()
    
    win.wait_window()
    return result[0]


def main():
    root = tk.Tk()
    root.withdraw()
    apply_app_icon(root)
    
    config_repo = ConfigRepository(os.path.join(get_executable_dir(), "config.json"))
    translation_repo = TranslationRepository()
    
    config_service = ConfigService(config_repo)
    translation_service = TranslationService(translation_repo)
    
    config = config_service.load_config()

    theme_service = ThemeService(root)
    theme_service.configure_fonts(config.use_generic_font)
    normalized_theme = theme_service.normalize_theme_name(config.theme)
    config.theme = normalized_theme
    config_service.save_config(config)
    theme_service.set_theme(normalized_theme)
    
    if not config.language:
        language = show_language_selection_dialog(root, translation_service, theme_service, normalized_theme)
        if language:
            config.language = language
        else:
            config.language = "English"
        config_service.save_config(config)
    
    translation_service.load_language(config.language)
    root.title(versioned_title(translation_service.get("window.app_title", "Mewtator")))
    
    mod_repo = ModRepository(config.mod_folder)
    mod_service = ModService(mod_repo)
    dll_injection_service = DllInjectionService()
    launcher_service = GameLauncherService(dll_injection_service)
    pack_service = PackService()
    modlist_io_service = ModListIOService()
    
    controller = MainController(
        root,
        config_service,
        mod_service,
        launcher_service,
        translation_service,
        pack_service,
        modlist_io_service,
        theme_service,
        dll_injection_service
    )
    
    controller.start()

def _report_startup_failure() -> None:
    """Report startup exceptions..."""
    details = traceback.format_exc()
    try:
        log_dir = Path(get_executable_dir()) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "startup-error.log"
        log_path.write_text(details, encoding="utf-8")
    except Exception:
        log_path = None

    try:
        from tkinter import messagebox
        path_hint = f"\n\nDetails were written to:\n{log_path}" if log_path else ""
        messagebox.showerror(
            "Mewtator - Startup Error",
            "Mewtator could not finish starting." + path_hint,
        )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _report_startup_failure()
        raise
