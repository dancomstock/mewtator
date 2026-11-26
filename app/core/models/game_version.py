from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class GameVersionInfo:
    version: Optional[str] = None
    build: Optional[str] = None