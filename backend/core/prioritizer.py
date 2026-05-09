"""
Assign priority scores to findings and compute the overall debt score.

priority_score = severity_score / effort_score
  Severity: critical=4, high=3, medium=2, low=1
  Effort:   easy=1, medium=2, hard=3
"""
from backend.core.checkers import Finding
from backend.config import SEVERITY_SCORES, EFFORT_SCORES


def prioritize(findings: list[Finding]) -> list[Finding]:
    for f in findings:
        s = SEVERITY_SCORES.get(f.severity.lower(), 1)
        e = EFFORT_SCORES.get(f.effort.lower(), 2)
        f.priority_score = round(s / e, 2)

    findings.sort(key=lambda f: f.priority_score, reverse=True)
    return findings


def calculate_debt_score(findings: list[Finding]) -> int:
    """
    Returns an integer 0–100 where 100 = perfectly clean.
    Penalty accumulates by severity; 100+ weighted issues = 0.
    """
    if not findings:
        return 100

    penalty = sum(SEVERITY_SCORES.get(f.severity.lower(), 1) for f in findings)
    score = max(0, 100 - int(penalty / 1.5))
    return score


def build_summary(findings: list[Finding]) -> dict:
    return {
        "total": len(findings),
        "critical": sum(1 for f in findings if f.severity == "critical"),
        "high": sum(1 for f in findings if f.severity == "high"),
        "medium": sum(1 for f in findings if f.severity == "medium"),
        "low": sum(1 for f in findings if f.severity == "low"),
        "by_type": _count_by_type(findings),
        "by_file": _count_by_file(findings),
    }


def _count_by_type(findings: list[Finding]) -> dict:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.type] = counts.get(f.type, 0) + 1
    return counts


def _count_by_file(findings: list[Finding]) -> dict:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.file] = counts.get(f.file, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
