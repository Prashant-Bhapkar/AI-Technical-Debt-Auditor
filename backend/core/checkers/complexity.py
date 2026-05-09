"""
Flag functions whose cyclomatic complexity exceeds the configured threshold.
Complexity is stored in the symbols table by the indexer.
"""
from backend.core.checkers import Finding
from backend.core.graph import get_complex_functions
from backend.config import COMPLEXITY_THRESHOLD


def check(db_path: str, threshold: int = COMPLEXITY_THRESHOLD) -> list[Finding]:
    functions = get_complex_functions(db_path, threshold)
    findings = []

    for sym in functions:
        name = sym["name"]
        parent = sym.get("parent_class") or ""
        qualified = f"{parent}.{name}" if parent else name
        complexity = sym["complexity"]

        if complexity >= 20:
            severity = "critical"
        elif complexity >= 15:
            severity = "high"
        else:
            severity = "medium"

        findings.append(
            Finding(
                file=sym["file"],
                line=sym["line_start"],
                type="complexity",
                severity=severity,
                description=(
                    f"`{qualified}` has cyclomatic complexity {complexity} "
                    f"(threshold: {threshold})."
                ),
                why_it_matters=(
                    "High complexity means more paths through the code, "
                    "harder testing, and greater likelihood of subtle bugs."
                ),
                fix_suggestion=(
                    f"Refactor `{qualified}` by extracting logical sub-tasks "
                    "into smaller, focused helper functions. "
                    "Aim for complexity ≤ 10 per function."
                ),
                effort="medium" if complexity < 20 else "hard",
                function_name=qualified,
            )
        )

    return findings
