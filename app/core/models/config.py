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
    dll_injection_enabled: bool = False
    mewtator_intro_enabled: bool = True
    use_generic_font: bool = False
    linux_allow_undefined_steam_runtime_or_proton: bool = False
    linux_steam_gameoverlayrenderer_disabled: bool = False
    linux_steam_runtime_path: str = ""
    linux_proton_path: str = ""
    linux_compatdata_override_dir: str = ""
    concurrent_launches_enabled: bool = False
    always_ungraceful_stop_enabled: bool = False
    
    def is_valid(self) -> bool:
        """Return whether Mewtator has enough configuration to open its main UI...
        """
        return bool(
            self.game_install_dir
            and os.path.isdir(self.game_install_dir)
            and self.mod_folder
            and os.path.isdir(self.mod_folder)
        )

    def normalize_paths(self):
        if self.game_install_dir:
            self.game_install_dir = os.path.normpath(self.game_install_dir)
        if self.mod_folder:
            self.mod_folder = os.path.normpath(self.mod_folder)
        if self.linux_steam_runtime_path:
            self.linux_steam_runtime_path = os.path.normpath(self.linux_steam_runtime_path)
        if self.linux_proton_path:
            self.linux_proton_path = os.path.normpath(self.linux_proton_path)
        if self.linux_compatdata_override_dir:
            self.linux_compatdata_override_dir = os.path.normpath(self.linux_compatdata_override_dir)
 
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
            "dll_injection_enabled": self.dll_injection_enabled,
            "mewtator_intro_enabled": self.mewtator_intro_enabled,
            "use_generic_font": self.use_generic_font,
            'linux_allow_undefined_steam_runtime_or_proton': self.linux_allow_undefined_steam_runtime_or_proton,
            'linux_steam_gameoverlayrenderer_disabled': self.linux_steam_gameoverlayrenderer_disabled,
            "linux_steam_runtime_path": self.linux_steam_runtime_path,
            "linux_proton_path": self.linux_proton_path,
            "linux_compatdata_override_dir": self.linux_compatdata_override_dir,
            "concurrent_launches_enabled": self.concurrent_launches_enabled,
            "always_ungraceful_stop_enabled": self.always_ungraceful_stop_enabled
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
            dll_injection_enabled=data.get("dll_injection_enabled", False),
            mewtator_intro_enabled=data.get("mewtator_intro_enabled", True),
            use_generic_font=data.get("use_generic_font", False),
            linux_allow_undefined_steam_runtime_or_proton=data.get("linux_allow_undefined_steam_runtime_or_proton", False),
            linux_steam_gameoverlayrenderer_disabled=data.get("linux_steam_gameoverlayrenderer_disabled", False),
            linux_steam_runtime_path=data.get("linux_steam_runtime_path", ""),
            linux_proton_path=data.get("linux_proton_path", ""),
            linux_compatdata_override_dir=data.get("linux_compatdata_override_dir", ""),
            concurrent_launches_enabled=data.get("concurrent_launches_enabled", False),
            always_ungraceful_stop_enabled=data.get("always_ungraceful_stop_enabled", False)
        )
