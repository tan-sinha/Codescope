from dataclasses import dataclass, field


@dataclass
class CallEdge:
    caller: str
    callee: str
    resolved: bool = False
    raw_text: str | None = None


@dataclass
class FunctionCalls:
    function: str
    calls: list[CallEdge] = field(default_factory=list)

from dataclasses import dataclass


@dataclass
class ResolutionStats:
    total_calls: int = 0
    resolved_calls: int = 0

    @property
    def resolution_rate(self):
        if self.total_calls == 0:
            return 0.0

        return (
            self.resolved_calls
            / self.total_calls
        ) * 100