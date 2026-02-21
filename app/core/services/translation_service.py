from typing import Dict, Any
from app.infrastructure.translation_repository import TranslationRepository


class TranslationService:
    def __init__(self, repository: TranslationRepository):
        self.repository = repository
        self.current_language = "English"
        self.translations: Dict[str, Any] = {}
        self.load_language("English")
    
    def load_language(self, language: str):
        self.current_language = language
        self.translations = self.repository.load_translations(language)
    
    def get(self, key: str, default: str = None) -> str:
        parts = key.split(".")
        value = self.translations
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default or key
        
        return value if value else (default or key)
    
    def get_available_languages(self) -> list:
        return self.repository.get_available_languages()
