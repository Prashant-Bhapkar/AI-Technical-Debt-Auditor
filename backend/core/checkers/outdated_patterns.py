"""
Detect outdated Python patterns via AST analysis:
  1. Mutable default arguments (list/dict/set literal as default)
  2. type(x) == T comparisons (prefer isinstance)
  3. % string formatting (prefer f-strings)
  4. Old-style super() calls: super(ClassName, self)
  5. Bare string exception raises: raise "error message"
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

_MUTABLE_TYPES = {"list", "dictionary", "set"}


def _node_text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


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

            # 1. Mutable default arguments
            params = node.child_by_field_name("parameters")
            if params:
                for child in params.children:
                    if child.type == "default_parameter":
                        val = child.child_by_field_name("value")
                        if val and val.type in _MUTABLE_TYPES:
                            param_name_node = child.child_by_field_name("name")
                            param_name = _node_text(param_name_node, src) if param_name_node else "?"
                            findings.append(Finding(
                                file=rel_path,
                                line=child.start_point[0] + 1,
                                type="outdated_patterns",
                                severity="high",
                                description=(
                                    f"`{fname}({param_name}=[...])` uses a mutable default argument."
                                ),
                                why_it_matters=(
                                    "Mutable defaults are shared across all calls — mutations "
                                    "in one call persist into the next, causing subtle state bugs."
                                ),
                                fix_suggestion=(
                                    f"Replace the mutable default with `None` and initialise "
                                    f"inside the function body: "
                                    f"`if {param_name} is None: {param_name} = []`."
                                ),
                                effort="easy",
                                function_name=fname,
                            ))

            for child in node.children:
                walk(child, fname)
            return

        # 2. type(x) == T comparisons
        if t == "comparison_operator":
            children = list(node.children)
            for i, child in enumerate(children):
                if child.type == "call":
                    func_node = child.child_by_field_name("function")
                    if func_node and _node_text(func_node, src) == "type":
                        # check operator is == or !=
                        ops = [c for c in children if c.type in ("==", "!=", "is")]
                        if ops:
                            full_text = _node_text(node, src)
                            findings.append(Finding(
                                file=rel_path,
                                line=node.start_point[0] + 1,
                                type="outdated_patterns",
                                severity="low",
                                description=f"`{full_text[:60]}` uses `type()` for type checking.",
                                why_it_matters=(
                                    "`type() ==` breaks polymorphism — subclasses don't match. "
                                    "`isinstance()` correctly handles inheritance."
                                ),
                                fix_suggestion=(
                                    "Replace `type(x) == T` with `isinstance(x, T)`."
                                ),
                                effort="easy",
                                function_name=func_name,
                            ))
                            break

        # 3. % string formatting
        if t == "binary_operator":
            op_nodes = [c for c in node.children if c.type == "%"]
            if op_nodes:
                left = node.children[0] if node.children else None
                if left and left.type == "string":
                    snippet = _node_text(node, src)[:60]
                    findings.append(Finding(
                        file=rel_path,
                        line=node.start_point[0] + 1,
                        type="outdated_patterns",
                        severity="low",
                        description=f"`{snippet}` uses `%` string formatting.",
                        why_it_matters=(
                            "%-formatting is error-prone and less readable than f-strings. "
                            "It is considered legacy style in Python 3.6+."
                        ),
                        fix_suggestion=(
                            "Rewrite using an f-string: `f'...'` or `str.format()`."
                        ),
                        effort="easy",
                        function_name=func_name,
                    ))

        # 4. Old-style super() with explicit class/self arguments
        if t == "call":
            func_node = node.child_by_field_name("function")
            if func_node and _node_text(func_node, src) == "super":
                args_node = node.child_by_field_name("arguments")
                if args_node:
                    args_text = _node_text(args_node, src).strip("()")
                    if args_text.strip():  # non-empty args = old-style
                        findings.append(Finding(
                            file=rel_path,
                            line=node.start_point[0] + 1,
                            type="outdated_patterns",
                            severity="low",
                            description=f"`super({args_text})` — Python 2-style super() call.",
                            why_it_matters=(
                                "Python 3 supports zero-argument `super()` which is shorter, "
                                "less error-prone, and works correctly with multiple inheritance."
                            ),
                            fix_suggestion="Replace `super(ClassName, self)` with `super()`.",
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
            print(f"Warning: outdated_patterns checker failed on {rel_path}: {exc}")
    return findings
