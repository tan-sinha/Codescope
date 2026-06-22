from dataclasses import dataclass, field


@dataclass
class ModuleInfo:
    path: str

    functions: list[str] = field(
        default_factory=list
    )

    classes: list[str] = field(
        default_factory=list
    )

    imports: list[str] = field(
        default_factory=list
    )

    summary: str | None = None
    summary_source: str | None = None