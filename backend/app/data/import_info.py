from dataclasses import dataclass, field


@dataclass
class ImportInfo:
    module: str
    names: list[str] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    is_relative: bool = False
    relative_level: int = 0
    resolved_path: str | None = None