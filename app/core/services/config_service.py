from app.core.models.config import Config
from app.infrastructure.config_repository import ConfigRepository


class ConfigService:
    def __init__(self, repository: ConfigRepository):
        self.repository = repository
    
    def load_config(self) -> Config:
        config = self.repository.load()
        
        if config is None:
            config = Config()
        
        if not config.mod_folder:
            import os
            config.mod_folder = os.path.join(os.getcwd(), "mods")
        
        config.normalize_paths()
        return config
    
    def save_config(self, config: Config):
        config.normalize_paths()
        self.repository.save(config)
    
    def validate_config(self, config: Config) -> bool:
        return config.is_valid()
