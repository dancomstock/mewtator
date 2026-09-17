from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class GonBinding:
    file_path: str
    relative_path: str
    object_path: str
    raw_value: str

    @property
    def display_target(self) -> str:
        return f"{self.relative_path} :: {self.object_path}"

@dataclass
class ModConfigOption:
    section: str
    key: str
    raw_value: str
    value: Any
    control_type: str
    line_index: int
    prefix: str
    suffix: str
    newline: str
    tooltip: str = ""
    label: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    enum_values: List[str] = field(default_factory=list)
    has_default: bool = False
    default_value: Any = None
    default_error: str = ""
    bool_true: str = "1"
    bool_false: str = "0"
    quote: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    gon_binding: Optional[GonBinding] = None
    gon_binding_error: str = ""

    @property
    def display_label(self) -> str:
        return self.label or self.key

    @property
    def identifier(self) -> int:
        # Line number is stable for the lifetime of one parsed config, 
        # also permits duplicate keys without silently collapsing them... - Tim
        return self.line_index

    @property
    def is_gon_bound(self) -> bool:
        return self.gon_binding is not None

@dataclass
class ModConfigSection:
    name: str
    options: List[ModConfigOption] = field(default_factory=list)

@dataclass
class ModConfig:
    path: str
    sections: List[ModConfigSection]
    lines: List[str]
    encoding: str = "utf-8"
    has_bom: bool = False
    gui_enabled: bool = True
    primary: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def options(self) -> List[ModConfigOption]:
        return [option for section in self.sections for option in section.options]