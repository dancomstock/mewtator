import json
import os
from typing import Optional
from app.core.models.config import Config


class ConfigRepository:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
    
    def load(self) -> Optional[Config]:
        if not os.path.exists(self.config_path):
            self.save(Config())
            return None
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = Config.from_dict(data)
                config.normalize_paths()
                return config
        except (json.JSONDecodeError, IOError):
            self.save(Config())
            return None
    
    def save(self, config: Config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=4)
