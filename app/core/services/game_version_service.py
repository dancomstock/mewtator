import re
from pathlib import Path
from typing import Optional, Tuple

class GameVersionService:
    VERSION_MARKER = re.compile(
        rb"MEWGENICSEXEVERSIONINFO\|([^|\x00]+)\|([^|\x00]+)\|"
    )

    @classmethod
    def read_executable_version(cls, executable_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Reads the game's version and build from static embedded string!"""
        try:
            contents = Path(executable_path).read_bytes()
        except OSError:
            return None, None

        match = cls.VERSION_MARKER.search(contents)
        
        if not match:
            return None, None

        try:
            version, build = (value.decode("ascii") for value in match.groups())
        except UnicodeDecodeError:
            return None, None

        return version, build