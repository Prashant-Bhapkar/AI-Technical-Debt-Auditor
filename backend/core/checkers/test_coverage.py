"""
Detect public functions/methods that appear to have no test coverage.

Strategy:
  1. Collect all public function/method names from non-test source files (via db).
  2. Find all test files (test_*.py / *_test.py) under source_root.
  3. Read test file text; if the function name does not appear anywhere in any
     test file, flag it as untested.

This is a name-reference heuristic — it cannot catch indirect testing but
catches the common case of a function with zero test references.
"""
import os
import re
import sqlite3
from pathlib import Path

from backend.core.checkers import Finding
from backend.config import IGNORE_PATTERNS

_TEST_FILE_RE = re.compile(r"(^|[\\/])(test_[^/\\]+|[^/\\]+_test)\.py$", re.IGNORECASE)
_PRIVATE_RE = re.compile(r"^_")


def _is_test_file(rel_path: str) -> bool:
    return bool(_TEST_FILE_RE.search(rel_path.replace("\\", "/")))


def check(db_path: str, source_root: str) -> list[Finding]:
    conn = sqlite3.connect(db_path)

    # Public functions/methods in non-test files
    rows = conn.execute(
        "SELECT name, file, line_start FROM symbols "
        "WHERE type IN ('function', 'method') ORDER BY file, line_start"
    ).fetchall()
    conn.close()

    # Build test corpus: concatenated text of all test files
    test_text = ""
    test_files_found = 0
    for root, dirs, fnames in os.walk(source_root):
        # Prune ignored directories so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for fname in fnames:
            if not fname.endswith(".py"):
                continue
            abs_path = os.path.join(root, fname)
            rel = os.path.relpath(abs_path, source_root).replace("\\", "/")
            if _is_test_file(rel):
                try:
                    test_text += Path(abs_path).read_text(encoding="utf-8", errors="replace")
                    test_files_found += 1
                except Exception:
                    pass

    if test_files_found == 0:
        # No test files at all — single project-level finding
        return [
            Finding(
                file="<project>",
                line=0,
                type="test_coverage",
                severity="high",
                description="No test files found in this project.",
                why_it_matters=(
                    "Without tests, regressions go undetected and refactoring "
                    "becomes unsafe."
                ),
                fix_suggestion=(
                    "Create a `tests/` directory with `test_*.py` files. "
                    "Start with pytest: `pip install pytest` and `pytest tests/`."
                ),
                effort="hard",
                function_name="<project>",
            )
        ]

    findings: list[Finding] = []
    for func_name, rel_path, line in rows:
        if _PRIVATE_RE.match(func_name):
            continue
        if _is_test_file(rel_path):
            continue
        if func_name in ("__init__", "__str__", "__repr__", "__len__", "__eq__"):
            continue
        if func_name not in test_text:
            findings.append(Finding(
                file=rel_path,
                line=line,
                type="test_coverage",
                severity="medium",
                description=f"`{func_name}` has no apparent test coverage.",
                why_it_matters=(
                    "Untested public functions are invisible regression surfaces — "
                    "any change could introduce a bug that ships silently."
                ),
                fix_suggestion=(
                    f"Add a test function `test_{func_name}()` in the relevant "
                    f"`test_*.py` file that exercises the main code paths."
                ),
                effort="medium",
                function_name=func_name,
            ))

    return findings
