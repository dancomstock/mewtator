import json
import os
from pathlib import Path

class Translator:
    def __init__(self, language="English"):
        self.language = language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        lang_dir = Path(__file__).parent / "locales"
        lang_file = lang_dir / f"{self.language}.json"
        
        # Always load English as fallback
        fallback_file = lang_dir / "English.json"
        if fallback_file.exists():
            with open(fallback_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        
        # Override with requested language if different
        if lang_file.exists() and self.language != "English":
            with open(lang_file, "r", encoding="utf-8") as f:
                lang_data = json.load(f)
                self.translations.update(lang_data)
    
    def get(self, key, default=None):
        """Translate a key like 'menu.file.settings' or use English fallback"""
        parts = key.split(".")
        value = self.translations
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default or key
        return value if value else (default or key)

# Global translator instance
_translator = None

def init_translator(language="English"):
    global _translator
    _translator = Translator(language)

def t(key, default=None):
    """Shorthand for translate"""
    global _translator
    if _translator is None:
        init_translator()
    return _translator.get(key, default)