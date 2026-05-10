"""
Detect missing observability patterns via AST analysis:
  1. Non-trivial functions (>= MIN_LINES body) with no logging calls
  2. except blocks that silently discard exceptions (pass / continue)
"""
import os
import sqlite3
from pathlib import Path

from backend.core.checkers import Finding

MIN_FUNCTION_LINES = 8  # only flag functions at least this many lines long

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

_LOGGING_CALLEES = {
    "logging.debug", "logging.info", "logging.warning", "logging.error",
    "logging.critical", "logging.exception", "logging.log",
    "logger.debug", "logger.info", "logger.warning", "logger.error",
    "logger.critical", "logger.exception",
    "log.debug", "log.info", "log.warning", "log.error",
    "log.critical", "log.exception",
    "self.logger.debug", "self.logger.info", "self.logger.warning",
    "self.logger.error", "self.logger.critical",
    "print",
}


def _node_text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _has_logging(node, src: bytes) -> bool:
    """Recursively check if any call inside node is a logging call."""
    if node.type == "call":
        func = node.child_by_field_name("function")
        if func:
            callee = _node_text(func, src)
            if callee in _LOGGING_CALLEES or callee.endswith(
                (".debug", ".info", ".warning", ".error", ".critical", ".exception")
            ):
                return True
    return any(_has_logging(child, src) for child in node.children)


def _is_silent_except(handler_node, src: bytes) -> bool:
    """Return True if except block only contains pass/continue/ellipsis."""
    body_stmts = [
        c for c in handler_node.children
        if c.type not in ("except_clause", ":", "comment")
        and c.type not in ("identifier", "as_pattern")
    ]
    for stmt in body_stmts:
        if stmt.type not in ("pass_statement", "continue_statement", "expression_statement"):
            return False
        if stmt.type == "expression_statement":
            inner = stmt.children[0] if stmt.children else None
            if inner and inner.type == "ellipsis":
                continue
            return False
    return True


def _scan_file(src: bytes, rel_path: str) -> list[Finding]:
    if not _AVAILABLE:
        return []

    tree = _py_parser.parse(src)
    findings: list[Finding] = []

    def walk(node, func_name: str):
        t = node.type

        if t in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            fname = _node_text(name_node, src) if name_node else "unknown"
            body_node = node.child_by_field_name("body")

            if body_node:
                start = node.start_point[0]
                end = node.end_point[0]
                line_count = end - start

                if line_count >= MIN_FUNCTION_LINES and not _has_logging(body_node, src):
                    findings.append(Finding(
                        file=rel_path,
                        line=node.start_point[0] + 1,
                        type="observability",
                        severity="medium",
                        description=(
                            f"`{fname}` has {line_count} lines but no logging calls."
                        ),
                        why_it_matters=(
                            "Without logging, failures and slow paths in production are "
                            "invisible — debugging requires reproducing the issue locally."
                        ),
                        fix_suggestion=(
                            f"Add `import logging` and instrument `{fname}` with "
                            "`logging.info(...)` at entry and `logging.exception(...)` "
                            "in exception handlers."
                        ),
                        effort="easy",
                        function_name=fname,
                    ))

                # walk function body for nested functions and try/except
                for child in node.children:
                    walk(child, fname)
            return

        # Silent exception swallowing
        if t == "except_clause":
            # find the parent try_statement's except_clause body
            parent = node.parent
            if parent and parent.type == "try_statement":
                # each except_clause is followed by a block
                siblings = list(parent.children)
                idx = siblings.index(node)
                handler_body = siblings[idx + 1] if idx + 1 < len(siblings) else None
                if handler_body and handler_body.type == "block":
                    if _is_silent_except(handler_body, src) and not _has_logging(handler_body, src):
                        findings.append(Finding(
                            file=rel_path,
                            line=node.start_point[0] + 1,
                            type="observability",
                            severity="high",
                            description=(
                                f"Silent exception in `{func_name}` — "
                                "exception swallowed without logging."
                            ),
                            why_it_matters=(
                                "Silently catching exceptions hides bugs and makes production "
                                "failures impossible to diagnose without a debugger."
                            ),
                            fix_suggestion=(
                                "Add `logging.exception('...')` or `logger.exception('...')` "
                                "inside the except block to capture the full traceback."
                            ),
                            effort="easy",
                            function_name=func_name,
                        ))

        for child in node.children:
            walk(child, func_name)

    walk(tree.root_node, "<module>")
    return findings


def check(db_path: str, source_root: str) -> list[Finding]:
    if not _AVAILABLE:
        return []

    conn = sqlite3.connect(db_path)
    files = [row[0] for row in conn.execute("SELECT DISTINCT file FROM symbols ORDER BY file")]
    conn.close()

    findings: list[Finding] = []
    for rel_path in files:
        abs_path = os.path.join(source_root, rel_path.replace("/", os.sep))
        if not Path(abs_path).exists():
            continue
        try:
            findings.extend(_scan_file(Path(abs_path).read_bytes(), rel_path))
        except Exception as exc:
            print(f"Warning: observability checker failed on {rel_path}: {exc}")
    return findings
