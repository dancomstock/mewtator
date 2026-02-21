import json
import os
import sys
from pathlib import Path
from typing import Dict, Any


class TranslationRepository:
    def __init__(self):
        self._get_locales_dir()
    
    def _get_locales_dir(self) -> Path:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent / "locales"
        else:
            return Path(__file__).parent.parent.parent / "locales"
    
    def load_translations(self, language: str) -> Dict[str, Any]:
        lang_dir = self._get_locales_dir()
        
        fallback_file = lang_dir / "English.json"
        translations = {}
        
        if fallback_file.exists():
            with open(fallback_file, "r", encoding="utf-8") as f:
                translations = json.load(f)
        
        if language != "English":
            lang_file = lang_dir / f"{language}.json"
            if lang_file.exists():
                with open(lang_file, "r", encoding="utf-8") as f:
                    lang_data = json.load(f)
                    translations.update(lang_data)
        
        return translations
    
    def get_available_languages(self) -> list:
        lang_dir = self._get_locales_dir()
        
        langs = []
        if lang_dir.exists():
            for file in lang_dir.glob("*.json"):
                langs.append(file.stem)
        
        if not langs:
            return ["English"]
        
        langs = sorted(langs)
        
        if "English" in langs:
            langs.remove("English")
            langs.insert(0, "English")
        
        return langs
