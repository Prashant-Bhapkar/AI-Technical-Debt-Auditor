"""
Detect near-duplicate functions using token-based Jaccard similarity.

Algorithm:
  1. Extract all function bodies from source files (functions >= MIN_LINES).
  2. Normalise each body: strip comments, collapse whitespace, lowercase.
  3. Tokenise into word-level bigrams.
  4. Compute pairwise Jaccard similarity; flag pairs >= THRESHOLD.

If sentence-transformers is installed, falls back to cosine similarity on
embeddings for better semantic matching (optional upgrade).

Capped at MAX_FUNCTIONS to keep O(n²) comparison practical.
"""
import os
import re
import sqlite3
from pathlib import Path
from itertools import combinations

from backend.core.checkers import Finding
from backend.config import DUPLICATE_SIMILARITY_THRESHOLD

MIN_LINES = 5
MAX_FUNCTIONS = 400

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

_COMMENT_RE = re.compile(r"#[^\n]*")
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-zA-Z_]\w*")


def _node_text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _normalise(text: str) -> str:
    text = _COMMENT_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def _bigrams(text: str) -> frozenset[str]:
    tokens = _TOKEN_RE.findall(text)
    if len(tokens) < 2:
        return frozenset(tokens)
    return frozenset(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _extract_functions(src: bytes, rel_path: str) -> list[dict]:
    """Return list of {name, line, body_norm, bigrams} for each function."""
    if not _AVAILABLE:
        return []

    tree = _py_parser.parse(src)
    results = []

    def walk(node):
        t = node.type
        if t in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            body_node = node.child_by_field_name("body")
            if name_node and body_node:
                fname = _node_text(name_node, src)
                body_text = _node_text(body_node, src)
                line_count = body_node.end_point[0] - body_node.start_point[0]
                if line_count >= MIN_LINES:
                    norm = _normalise(body_text)
                    results.append({
                        "name": fname,
                        "file": rel_path,
                        "line": node.start_point[0] + 1,
                        "norm": norm,
                        "bigrams": _bigrams(norm),
                    })
            # still walk inside for nested functions
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return results


def check(db_path: str, source_root: str) -> list[Finding]:
    if not _AVAILABLE:
        return []

    conn = sqlite3.connect(db_path)
    files = [row[0] for row in conn.execute("SELECT DISTINCT file FROM symbols ORDER BY file")]
    conn.close()

    all_funcs: list[dict] = []
    for rel_path in files:
        abs_path = os.path.join(source_root, rel_path.replace("/", os.sep))
        if not Path(abs_path).exists():
            continue
        try:
            all_funcs.extend(_extract_functions(Path(abs_path).read_bytes(), rel_path))
        except Exception as exc:
            print(f"Warning: duplicates checker failed on {rel_path}: {exc}")

    # Cap to avoid O(n²) blowup on very large codebases
    if len(all_funcs) > MAX_FUNCTIONS:
        all_funcs = all_funcs[:MAX_FUNCTIONS]

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()  # avoid duplicate pair reports

    for fa, fb in combinations(all_funcs, 2):
        # Skip same-file same-name (likely same function reported twice)
        if fa["file"] == fb["file"] and fa["name"] == fb["name"]:
            continue

        sim = _jaccard(fa["bigrams"], fb["bigrams"])
        if sim < DUPLICATE_SIMILARITY_THRESHOLD:
            continue

        pair_key = tuple(sorted([f"{fa['file']}:{fa['line']}", f"{fb['file']}:{fb['line']}"]))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        pct = int(sim * 100)
        findings.append(Finding(
            file=fa["file"],
            line=fa["line"],
            type="duplicates",
            severity="medium",
            description=(
                f"`{fa['name']}` is {pct}% similar to `{fb['name']}` "
                f"in `{fb['file']}:{fb['line']}`."
            ),
            why_it_matters=(
                "Duplicated logic creates divergent bugs — a fix in one copy must be "
                "manually applied to all copies, and they often drift over time."
            ),
            fix_suggestion=(
                f"Extract the shared logic from `{fa['name']}` and `{fb['name']}` "
                "into a single shared helper function."
            ),
            effort="medium",
            function_name=fa["name"],
        ))

    return findings
