"""Generate a Markdown audit report."""
from __future__ import annotations

from datetime import datetime, timezone

TYPE_LABELS = {
    "dead_code": "Dead Code",
    "complexity": "Complexity",
    "error_handling": "Error Handling",
    "duplicates": "Duplicates",
    "security": "Security",
    "observability": "Observability",
    "test_coverage": "Test Coverage",
    "outdated_patterns": "Outdated Patterns",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🔵",
}


def generate(result: dict, audit_id: str) -> str:
    score = result.get("score", 0)
    summary = result.get("summary", {})
    findings = result.get("findings", [])
    source_path = result.get("source_path", audit_id)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ai = result.get("ai_insights", {})

    lines: list[str] = []
    lines.append(f"# Technical Debt Report")
    lines.append(f"")
    lines.append(f"**Source:** `{source_path}`  ")
    lines.append(f"**Generated:** {generated_at}  ")
    lines.append(f"**Debt Score:** {score}/100")
    lines.append(f"")

    # Summary
    lines.append("## Summary")
    lines.append(f"")
    lines.append(f"| Severity | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| 🔴 Critical | {summary.get('critical', 0)} |")
    lines.append(f"| 🟠 High     | {summary.get('high', 0)} |")
    lines.append(f"| 🟡 Medium   | {summary.get('medium', 0)} |")
    lines.append(f"| 🔵 Low      | {summary.get('low', 0)} |")
    lines.append(f"| **Total**  | **{summary.get('total', 0)}** |")
    lines.append(f"")

    # By type
    by_type = summary.get("by_type", {})
    if by_type:
        lines.append("### By Type")
        lines.append(f"")
        lines.append(f"| Type | Count |")
        lines.append(f"|------|-------|")
        for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {TYPE_LABELS.get(k, k)} | {v} |")
        lines.append(f"")

    # AI insights
    if ai and ai.get("available"):
        lines.append("## AI Analysis")
        lines.append(f"")
        if ai.get("summary"):
            lines.append(ai["summary"])
            lines.append(f"")
        if ai.get("top_issues"):
            lines.append("### Top Issues")
            for issue in ai["top_issues"]:
                lines.append(f"- {issue}")
            lines.append(f"")
        if ai.get("recommended_steps"):
            lines.append("### Recommended Steps")
            for i, step in enumerate(ai["recommended_steps"], 1):
                lines.append(f"{i}. {step}")
            lines.append(f"")
        if ai.get("architecture_notes"):
            lines.append(f"*{ai['architecture_notes']}*")
            lines.append(f"")

    # Findings
    lines.append(f"## Findings ({len(findings)})")
    lines.append(f"")

    current_type = None
    for f in findings:
        ftype = f.get("type", "")
        if ftype != current_type:
            current_type = ftype
            lines.append(f"### {TYPE_LABELS.get(ftype, ftype)}")
            lines.append(f"")

        sev = f.get("severity", "low")
        emoji = SEVERITY_EMOJI.get(sev, "⚪")
        lines.append(
            f"#### {emoji} `{f.get('file','')}:{f.get('line','')}` — {f.get('description','')[:100]}"
        )
        lines.append(f"")
        if f.get("function_name") and f["function_name"] != "<module>":
            lines.append(f"**Function:** `{f['function_name']}`  ")
        lines.append(f"**Severity:** {sev} | **Effort:** {f.get('effort','')} | **Score:** {f.get('priority_score',0)}")
        lines.append(f"")
        lines.append(f"> **Why it matters:** {f.get('why_it_matters','')}")
        lines.append(f"")
        lines.append(f"**Fix:** {f.get('fix_suggestion','')}")
        lines.append(f"")
        lines.append("---")
        lines.append(f"")

    return "\n".join(lines)
