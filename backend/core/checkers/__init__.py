from dataclasses import dataclass, field


@dataclass
class Finding:
    file: str
    line: int
    type: str
    severity: str          # critical | high | medium | low
    description: str
    why_it_matters: str
    fix_suggestion: str
    effort: str            # easy | medium | hard
    priority_score: float = 0.0
    function_name: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "why_it_matters": self.why_it_matters,
            "fix_suggestion": self.fix_suggestion,
            "effort": self.effort,
            "priority_score": round(self.priority_score, 2),
            "function_name": self.function_name,
        }
