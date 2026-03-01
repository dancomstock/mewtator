from dataclasses import dataclass
import os


@dataclass
class Config:
    game_install_dir: str = ""
    mod_folder: str = ""
    language: str = "English"
    theme: str = "dark"
    custom_launch_options: str = ""
    dev_mode_enabled: bool = False
    debug_console_enabled: bool = False
    # TEMPORARILY DISABLED: savefile_suffix_override: str = ""
    # TEMPORARILY DISABLED: inherit_save_override: str = ""
    close_on_launch: bool = False
    use_original_load_order: bool = False
    
    def is_valid(self) -> bool:
        return bool(
            self.game_install_dir 
            and self.mod_folder 
            and os.path.isdir(self.game_install_dir)
        )
    
    def normalize_paths(self):
        if self.game_install_dir:
            self.game_install_dir = os.path.normpath(self.game_install_dir)
        if self.mod_folder:
            self.mod_folder = os.path.normpath(self.mod_folder)
    
    def to_dict(self):
        return {
            "game_install_dir": self.game_install_dir,
            "mod_folder": self.mod_folder,
            "language": self.language,
            "theme": self.theme,
            "custom_launch_options": self.custom_launch_options,
            "dev_mode_enabled": self.dev_mode_enabled,
            "debug_console_enabled": self.debug_console_enabled,
            # TEMPORARILY DISABLED: "savefile_suffix_override": self.savefile_suffix_override,
            # TEMPORARILY DISABLED: "inherit_save_override": self.inherit_save_override,
            "close_on_launch": self.close_on_launch,
            "use_original_load_order": self.use_original_load_order,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            game_install_dir=data.get("game_install_dir", ""),
            mod_folder=data.get("mod_folder", ""),
            language=data.get("language", "English"),
            theme=data.get("theme", "dark"),
            custom_launch_options=data.get("custom_launch_options", ""),
            dev_mode_enabled=data.get("dev_mode_enabled", False),
            debug_console_enabled=data.get("debug_console_enabled", False),
            # TEMPORARILY DISABLED: savefile_suffix_override=data.get("savefile_suffix_override", ""),
            # TEMPORARILY DISABLED: inherit_save_override=data.get("inherit_save_override", ""),
            close_on_launch=data.get("close_on_launch", False),
            use_original_load_order=data.get("use_original_load_order", False),
        )
