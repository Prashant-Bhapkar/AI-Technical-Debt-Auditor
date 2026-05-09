"""
Detect external calls (HTTP, file I/O, subprocess, DB) that are not wrapped
in a try/except block. Uses tree-sitter AST analysis on each source file.
"""
import os
import sqlite3
from pathlib import Path

from backend.core.checkers import Finding

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    PY_LANGUAGE = Language(tspython.language())

    def _make_parser():
        try:
            return Parser(PY_LANGUAGE)
        except TypeError:
            p = Parser()
            p.set_language(PY_LANGUAGE)
            return p

    _py_parser = _make_parser()
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False
    _py_parser = None

# Match against the callee expression only (not arguments) to avoid false positives
# from matching string literals inside arguments.
_CALLEE_PREFIXES = (
    "requests.", "httpx.", "subprocess.", "urllib.",
    "socket.", "ftplib.", "smtplib.", "paramiko.",
)
_CALLEE_SUFFIXES = (".execute", ".query", ".urlopen", ".open")
_CALLEE_EXACT = {"open", "urlopen"}


def _is_external_callee(callee: str) -> bool:
    callee = callee.strip()
    if callee in _CALLEE_EXACT:
        return True
    if any(callee.startswith(p) for p in _CALLEE_PREFIXES):
        return True
    if any(callee.endswith(s) for s in _CALLEE_SUFFIXES):
        return True
    return False


def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _callee_text(call_node, source_bytes: bytes) -> str:
    """Return only the callee expression (excludes arguments), e.g. 'requests.get'."""
    func = call_node.child_by_field_name("function")
    if func is None:
        return ""
    return _node_text(func, source_bytes)


def _scan_file(source_bytes: bytes, rel_path: str) -> list[Finding]:
    """Walk AST and find external calls not inside a try statement."""
    if not _AVAILABLE:
        return []

    tree = _py_parser.parse(source_bytes)
    findings = []

    def walk(node, in_try: bool, func_name: str):
        t = node.type

        if t == "try_statement":
            for child in node.children:
                walk(child, True, func_name)
            return

        if t in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            fname = _node_text(name_node, source_bytes) if name_node else "unknown"
            for child in node.children:
                walk(child, in_try, fname)
            return

        if t == "call" and not in_try:
            callee = _callee_text(node, source_bytes)
            if _is_external_callee(callee):
                short_callee = callee[:80]
                line = node.start_point[0] + 1
                findings.append(
                    Finding(
                        file=rel_path,
                        line=line,
                        type="error_handling",
                        severity="high",
                        description=(
                            f"`{short_callee}(...)` call has no error handling "
                            f"in `{func_name}`."
                        ),
                        why_it_matters=(
                            "Uncaught exceptions from I/O, network, or subprocess calls "
                            "can crash the application or leave resources in a broken state."
                        ),
                        fix_suggestion=(
                            f"Wrap `{short_callee}(...)` in a try/except block and "
                            "catch specific exceptions such as `OSError`, "
                            "`requests.RequestException`, or `subprocess.CalledProcessError`."
                        ),
                        effort="easy",
                        function_name=func_name,
                    )
                )

        for child in node.children:
            walk(child, in_try, func_name)

    walk(tree.root_node, False, "<module>")
    return findings


def check(db_path: str, source_root: str) -> list[Finding]:
    """Run error-handling checks across all indexed Python files."""
    if not _AVAILABLE:
        return []

    conn = sqlite3.connect(db_path)
    files = [
        row[0]
        for row in conn.execute("SELECT DISTINCT file FROM symbols ORDER BY file")
    ]
    conn.close()

    findings = []
    for rel_path in files:
        abs_path = os.path.join(source_root, rel_path.replace("/", os.sep))
        if not Path(abs_path).exists():
            continue
        try:
            source_bytes = Path(abs_path).read_bytes()
            findings.extend(_scan_file(source_bytes, rel_path))
        except Exception as exc:
            print(f"Warning: error_handling checker failed on {rel_path}: {exc}")

    return findings
