"""
Detect security anti-patterns via AST analysis:
  1. Hardcoded secrets (string assigned to variable with sensitive name)
  2. eval() / exec() calls
  3. subprocess / os.system with shell=True
  4. pickle.loads() / pickle.load()
  5. SQL injection risk via string formatting in .execute()
"""
import os
import re
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

_SECRET_NAME_RE = re.compile(
    r"(password|passwd|pwd|secret|api_key|apikey|token|auth_token|"
    r"access_key|private_key|credentials|client_secret|bearer)",
    re.IGNORECASE,
)
_SECRET_VALUE_SKIP_RE = re.compile(
    r"(your_|example|placeholder|changeme|<|>|\*{3,}|xxx|dummy|test|fake|mock|env\.|os\.)",
    re.IGNORECASE,
)


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
            for child in node.children:
                walk(child, fname)
            return

        # 1. Hardcoded secrets: identifier = "literal"
        if t == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left and right and right.type == "string":
                lhs = _node_text(left, src)
                # strip attribute prefix (self.password → password)
                bare = lhs.split(".")[-1]
                if _SECRET_NAME_RE.search(bare):
                    val = _node_text(right, src).strip("\"'")
                    if len(val) > 3 and not _SECRET_VALUE_SKIP_RE.search(val):
                        findings.append(Finding(
                            file=rel_path,
                            line=node.start_point[0] + 1,
                            type="security",
                            severity="critical",
                            description=f"Hardcoded secret in `{lhs}`.",
                            why_it_matters=(
                                "Credentials committed to source control can be leaked via "
                                "git history, logs, or error messages."
                            ),
                            fix_suggestion=(
                                f"Move `{bare}` to an environment variable: "
                                f"`os.getenv('{bare.upper()}')`."
                            ),
                            effort="easy",
                            function_name=func_name,
                        ))

        if t == "call":
            func_node = node.child_by_field_name("function")
            if func_node is None:
                for child in node.children:
                    walk(child, func_name)
                return

            callee = _node_text(func_node, src)

            # 2. eval() / exec()
            if callee in ("eval", "exec"):
                findings.append(Finding(
                    file=rel_path,
                    line=node.start_point[0] + 1,
                    type="security",
                    severity="critical",
                    description=f"`{callee}()` executes arbitrary Python code.",
                    why_it_matters=(
                        "Dynamic code execution is a remote code execution (RCE) vector "
                        "if any user-controlled data reaches this call."
                    ),
                    fix_suggestion=(
                        f"Replace `{callee}()` with a safe alternative: a lookup dict, "
                        "`ast.literal_eval()`, or explicit parsing logic."
                    ),
                    effort="medium",
                    function_name=func_name,
                ))

            # 3. subprocess with shell=True or os.system / os.popen
            if callee.startswith("subprocess.") or callee in ("os.system", "os.popen"):
                args_node = node.child_by_field_name("arguments")
                args_text = _node_text(args_node, src) if args_node else ""
                if "shell=True" in args_text or callee in ("os.system", "os.popen"):
                    findings.append(Finding(
                        file=rel_path,
                        line=node.start_point[0] + 1,
                        type="security",
                        severity="high",
                        description=f"`{callee}(...)` enables shell injection.",
                        why_it_matters=(
                            "Shell=True passes the command to /bin/sh; attacker-controlled "
                            "input can inject additional commands."
                        ),
                        fix_suggestion=(
                            "Pass a list of arguments and remove `shell=True`. "
                            "Validate all inputs before passing to subprocess."
                        ),
                        effort="medium",
                        function_name=func_name,
                    ))

            # 4. pickle.loads / pickle.load
            if callee in ("pickle.loads", "pickle.load"):
                findings.append(Finding(
                    file=rel_path,
                    line=node.start_point[0] + 1,
                    type="security",
                    severity="critical",
                    description=f"`{callee}()` deserializes potentially untrusted data.",
                    why_it_matters=(
                        "Unpickling attacker-controlled bytes executes arbitrary Python code."
                    ),
                    fix_suggestion=(
                        "Use JSON or another safe serialization format. "
                        "If pickle is required, verify the data's HMAC signature before loading."
                    ),
                    effort="medium",
                    function_name=func_name,
                ))

            # 5. SQL injection: .execute() / .executemany() with string formatting
            if callee.endswith((".execute", ".executemany")):
                args_node = node.child_by_field_name("arguments")
                if args_node:
                    args_text = _node_text(args_node, src)
                    if re.search(r'f["\']|%\s*\(|\.format\s*\(|"\s*\+|"\s*%', args_text):
                        findings.append(Finding(
                            file=rel_path,
                            line=node.start_point[0] + 1,
                            type="security",
                            severity="critical",
                            description=f"Possible SQL injection in `{callee}()` via string formatting.",
                            why_it_matters=(
                                "String-interpolated SQL lets attackers alter query structure "
                                "and read or modify arbitrary data."
                            ),
                            fix_suggestion=(
                                "Use parameterized queries: "
                                "`cursor.execute(sql, (param1, param2))` — "
                                "never build SQL via string concatenation or f-strings."
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
            print(f"Warning: security checker failed on {rel_path}: {exc}")
    return findings
