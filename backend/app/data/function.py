from dataclasses import dataclass, field


@dataclass
class Parameter:
    name: str
    annotation: str | None = None


@dataclass
class FunctionInfo:
    name: str
    parameters: list[Parameter] = field(default_factory=list)
    return_type: str | None = None
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    source_code: str = ""
    start_line: int = 0
    end_line: int = 0