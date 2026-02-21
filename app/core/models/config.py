from dataclasses import dataclass
import os


@dataclass
class Config:
    game_install_dir: str = ""
    mod_folder: str = ""
    language: str = "English"
    theme: str = "dark"
    
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
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            game_install_dir=data.get("game_install_dir", ""),
            mod_folder=data.get("mod_folder", ""),
            language=data.get("language", "English"),
            theme=data.get("theme", "dark"),
        )
