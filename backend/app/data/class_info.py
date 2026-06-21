from dataclasses import dataclass, field


@dataclass
class MethodSignature:
    name: str
    parameters: list[str]
    return_type: str | None = None


@dataclass
class ClassInfo:
    name: str
    base_classes: list[str] = field(default_factory=list)
    docstring: str | None = None
    methods: list[MethodSignature] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0