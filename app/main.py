import tkinter as tk
from tkinter import messagebox

from app.infrastructure.config_repository import ConfigRepository
from app.infrastructure.mod_repository import ModRepository
from app.infrastructure.translation_repository import TranslationRepository
from app.core.services.config_service import ConfigService
from app.core.services.mod_service import ModService
from app.core.services.game_launcher_service import GameLauncherService
from app.core.services.translation_service import TranslationService
from app.core.services.pack_service import PackService
from app.core.services.modlist_io_service import ModListIOService
from app.core.services.theme_service import ThemeService
from app.ui.controllers.main_controller import MainController
from app.ui.windows.settings_window import SettingsWindow


def show_language_selection_dialog(root, translation_service, theme_service, theme_name: str):
    from tkinter import Toplevel, StringVar
    from tkinter import ttk
    
    win = Toplevel(root)
    win.title(translation_service.get("window.dont_panic", "Don't Panic"))
    win.geometry("400x200")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    
    def on_closing():
        pass
    win.protocol("WM_DELETE_WINDOW", on_closing)
    
    result = [None]

    colors = theme_service.get_color_scheme(theme_name)
    win.configure(bg=colors["bg"])
    theme_service.apply_titlebar(win, theme_name)

    ttk.Label(
        win,
        text=translation_service.get("settings.select_language_title", "Select Language"),
        font=("Arial", 14, "bold")
    ).pack(pady=15)
    ttk.Label(
        win,
        text=translation_service.get("settings.select_language_text", "Choose your preferred language:")
    ).pack(pady=5)
    
    available_langs = translation_service.get_available_languages()
    if not available_langs:
        available_langs = ["English"]
    
    lang_var = StringVar(value=available_langs[0])
    
    lang_menu = ttk.Combobox(win, textvariable=lang_var, values=available_langs, state="readonly", width=30, height=15)
    lang_menu.pack(pady=10)
    
    def confirm():
        result[0] = lang_var.get()
        win.destroy()
    
    confirm_btn = ttk.Button(win, text=translation_service.get("settings.confirm", "Confirm"), command=confirm, width=20)
    confirm_btn.pack(pady=15)
    
    win.bind("<Return>", lambda e: confirm())
    win.bind("<KP_Enter>", lambda e: confirm())
    
    lang_menu.focus_set()
    
    win.wait_window()
    return result[0]


def main():
    root = tk.Tk()
    
    config_repo = ConfigRepository("config.json")
    translation_repo = TranslationRepository()
    
    config_service = ConfigService(config_repo)
    translation_service = TranslationService(translation_repo)
    
    config = config_service.load_config()

    theme_service = ThemeService(root)
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
    root.title(translation_service.get("window.app_title"))
    
    mod_repo = ModRepository(config.mod_folder)
    mod_service = ModService(mod_repo)
    launcher_service = GameLauncherService()
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
        theme_service
    )
    
    controller.start()


if __name__ == "__main__":
    main()
