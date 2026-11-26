import re
from pathlib import Path
from app.core.models.game_version import GameVersionInfo

class GameVersionService:
    VERSION_MARKER = re.compile(
        rb"MEWGENICSEXEVERSIONINFO\|([^|\x00]+)\|([^|\x00]+)\|"
    )

    @classmethod
    def read_executable_version(cls, executable_path: str) -> GameVersionInfo:
        """Reads the game's version and build from static embedded string!"""
        try:
            contents = Path(executable_path).read_bytes()
        except OSError:
            return GameVersionInfo()

        match = cls.VERSION_MARKER.search(contents)
        
        if not match:
            return GameVersionInfo()

        try:
            version, build = (value.decode("ascii") for value in match.groups())
        except UnicodeDecodeError:
            return GameVersionInfo()

        return GameVersionInfo(version=version, build=build)