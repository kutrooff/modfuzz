from dataclasses import dataclass, field

@dataclass
class AnalysisResult:

    issues: list[str] = field(default_factory=list)
    severity: str = "info"

