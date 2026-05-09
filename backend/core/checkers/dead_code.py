"""
Detect functions that have zero callers within the indexed codebase.
Uses the call graph stored in SQLite — purely deterministic, no AI.
"""
import sqlite3
from backend.core.checkers import Finding
from backend.core.graph import get_dead_code_candidates


def check(db_path: str) -> list[Finding]:
    candidates = get_dead_code_candidates(db_path)
    findings = []

    for sym in candidates:
        name = sym["name"]
        f = sym["file"]
        line = sym["line_start"]
        parent = sym.get("parent_class") or ""
        qualified = f"{parent}.{name}" if parent else name

        findings.append(
            Finding(
                file=f,
                line=line,
                type="dead_code",
                severity="medium",
                description=f"`{qualified}` is defined but never called within this codebase.",
                why_it_matters=(
                    "Dead code increases cognitive load, hides bugs, "
                    "and inflates the test surface without adding value."
                ),
                fix_suggestion=(
                    f"Remove `{qualified}` if it is truly unused. "
                    "If it is part of a public API, add a `# noqa: dead-code` comment "
                    "or export it explicitly."
                ),
                effort="easy",
                function_name=qualified,
            )
        )

    return findings
