import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class TranslationRepository:
    def __init__(self):
        self._get_locales_dir()

    def _get_locales_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent / "locales"
        return Path(__file__).parent.parent.parent / "locales"

    def _display_name_for_file(self, locale_file: Path) -> str:
        """Return the locale's declared display name, falling back to its filename..."""

        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata = data.get("_metadata", {}) if isinstance(data, dict) else {}
            display_name = metadata.get("language_name")
            if isinstance(display_name, str) and display_name.strip():
                return display_name.strip()
        except (OSError, json.JSONDecodeError, UnicodeError):
            pass

        return locale_file.stem

    def _find_language_file(self, language: str) -> Optional[Path]:
        lang_dir = self._get_locales_dir()

        if not lang_dir.exists():
            return None

        direct_file = lang_dir / f"{language}.json"

        if direct_file.exists():
            return direct_file

        for locale_file in lang_dir.glob("*.json"):
            if language == self._display_name_for_file(locale_file):
                return locale_file

        return None

    def normalize_language_name(self, language: str) -> str:
        """Return the locale's display name"""

        if not language:
            return "English"

        locale_file = self._find_language_file(language)

        if locale_file is None:
            return language
        
        return self._display_name_for_file(locale_file)

    def load_translations(self, language: str) -> Dict[str, Any]:
        lang_dir = self._get_locales_dir()
        fallback_file = lang_dir / "English.json"
        translations: Dict[str, Any] = {}

        if fallback_file.exists():
            with open(fallback_file, "r", encoding="utf-8") as f:
                translations = json.load(f)

        normalized = self.normalize_language_name(language)

        if normalized != "English":
            lang_file = self._find_language_file(normalized)

            if lang_file and lang_file.exists() and lang_file != fallback_file:
                with open(lang_file, "r", encoding="utf-8") as f:
                    lang_data = json.load(f)
                    translations.update(lang_data)

        return translations

    def get_available_languages(self) -> list:
        lang_dir = self._get_locales_dir()

        if not lang_dir.exists():
            return ["English"]

        langs = []
        seen = set()

        for locale_file in lang_dir.glob("*.json"):
            display_name = self._display_name_for_file(locale_file)

            if display_name not in seen:
                seen.add(display_name)
                langs.append(display_name)

        if not langs:
            return ["English"]

        langs.sort(key=str.casefold)
        
        if "English" in langs:
            langs.remove("English")
            langs.insert(0, "English")

        return langs
