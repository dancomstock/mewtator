import tkinter as tk
from tkinter import messagebox

from app.configloader import load_config, validate_config, save_config
from app.settings_window import open_settings_window, show_language_selection_dialog
from app.ui import build_ui, reload_ui
from app.i18n import init_translator, t


def main():
    cfg = load_config("config.json")
    
    root = tk.Tk()
    
    # Initialize translator with default language (before any UI)
    init_translator("English")
    
    # =======================================================
    # Create minimal config if needed
    # =======================================================
    if cfg is None:
        cfg = {"game_install_dir": "", "mod_folder": "", "language": ""}
        save_config("config.json", cfg)
    
    # =======================================================
    # Language Selection on First Startup
    # =======================================================
    if "language" not in cfg or not cfg.get("language"):
        language = show_language_selection_dialog(root)
        if language:
            cfg["language"] = language
            save_config("config.json", cfg)
            init_translator(language)
        else:
            # User cancelled, default to English
            cfg["language"] = "English"
            save_config("config.json", cfg)
            init_translator("English")
    else:
        # Initialize translator with saved language
        language = cfg.get("language", "English")
        init_translator(language)
    
    root.title(t("window.app_title"))

    # =======================================================
    # If config is missing or invalid → open settings
    # =======================================================
    if not validate_config(cfg):
        messagebox.showinfo(
            t("messages.setup_required_title"),
            t("messages.setup_required_text")
        )

        def after_settings(new_cfg, changed):
            reload_ui(root, new_cfg)

        open_settings_window(root, "config.json", after_settings)
        root.mainloop()
        return

    # -----------------------------------------------------
    # Config is valid → load UI
    # -----------------------------------------------------
    def after_settings(new_cfg, changed=None):
        reload_ui(root, new_cfg)

    build_ui(cfg, root, after_settings)
    root.mainloop()


if __name__ == "__main__":
    main()
