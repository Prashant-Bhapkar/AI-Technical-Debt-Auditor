"""Generate a JSON report from audit findings."""
import json
from backend.core.checkers import Finding


def generate(
    audit_id: str,
    score: int,
    findings: list[Finding],
    summary: dict,
    stats: dict,
) -> str:
    payload = {
        "audit_id": audit_id,
        "debt_score": score,
        "summary": summary,
        "graph_stats": stats,
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, indent=2)
