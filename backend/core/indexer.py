"""
Parse project files with tree-sitter, build SQLite call graph.
Schema: symbols, calls, imports, file_meta.
"""
import os
import sqlite3
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser, Node

    PY_LANGUAGE = Language(tspython.language())

    def _make_parser():
        try:
            return Parser(PY_LANGUAGE)
        except TypeError:
            p = Parser()
            p.set_language(PY_LANGUAGE)
            return p

    _py_parser = _make_parser()
    TREE_SITTER_AVAILABLE = True
except Exception as e:
    print(f"Warning: tree-sitter-python not available: {e}")
    TREE_SITTER_AVAILABLE = False
    _py_parser = None
    PY_LANGUAGE = None

from backend.config import IGNORE_PATTERNS, SUPPORTED_EXTENSIONS

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS symbols (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL,
    file        TEXT    NOT NULL,
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    complexity  INTEGER DEFAULT 1,
    loc         INTEGER DEFAULT 0,
    parent_class TEXT
);

CREATE TABLE IF NOT EXISTS calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id   INTEGER,
    callee_name TEXT    NOT NULL,
    callee_full TEXT,
    call_line   INTEGER,
    caller_file TEXT,
    FOREIGN KEY (caller_id) REFERENCES symbols(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS imports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    importer_file   TEXT NOT NULL,
    imported_module TEXT NOT NULL,
    imported_names  TEXT
);

CREATE TABLE IF NOT EXISTS file_meta (
    file        TEXT PRIMARY KEY,
    hash        TEXT NOT NULL,
    indexed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_symbols_name   ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file   ON symbols(file);
CREATE INDEX IF NOT EXISTS idx_calls_callee   ON calls(callee_name);
CREATE INDEX IF NOT EXISTS idx_calls_caller   ON calls(caller_id);
CREATE INDEX IF NOT EXISTS idx_imports_file   ON imports(importer_file);
"""


@dataclass
class IndexStats:
    files_processed: int = 0
    symbols_found: int = 0
    calls_found: int = 0
    imports_found: int = 0


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _should_ignore(path: str, source_root: str) -> bool:
    rel = os.path.relpath(path, source_root)
    parts = Path(rel).parts
    return any(part in IGNORE_PATTERNS for part in parts)


# ── Complexity ────────────────────────────────────────────────────────────────

_DECISION_TYPES = {
    "if_statement",
    "elif_clause",
    "for_statement",
    "while_statement",
    "except_clause",
    "boolean_operator",
    "conditional_expression",
    "with_statement",
}


def _calculate_complexity(node) -> int:
    complexity = 1

    def walk(n):
        nonlocal complexity
        if n.type in _DECISION_TYPES:
            complexity += 1
        for child in n.children:
            walk(child)

    walk(node)
    return complexity


# ── Symbol + Call extraction ──────────────────────────────────────────────────

def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_call_name(call_node, source_bytes: bytes) -> tuple[str, str]:
    """Return (callee_name, callee_full) for a call node."""
    func = call_node.child_by_field_name("function")
    if func is None:
        return "", ""

    if func.type == "identifier":
        name = _node_text(func, source_bytes)
        return name, name

    if func.type == "attribute":
        attr = func.child_by_field_name("attribute")
        attr_name = _node_text(attr, source_bytes) if attr else ""
        full = _node_text(func, source_bytes)
        return attr_name, full

    return "", ""


def _extract_imports(root, source_bytes: bytes, filepath: str, conn: sqlite3.Connection):
    def walk(n):
        if n.type == "import_statement":
            for child in n.children:
                if child.type == "dotted_name":
                    mod = _node_text(child, source_bytes)
                    conn.execute(
                        "INSERT INTO imports (importer_file, imported_module) VALUES (?,?)",
                        (filepath, mod),
                    )

        elif n.type == "import_from_statement":
            mod_node = n.child_by_field_name("module_name")
            mod = _node_text(mod_node, source_bytes) if mod_node else ""
            names = []
            for child in n.children:
                if child.type in ("dotted_name", "aliased_import"):
                    names.append(_node_text(child, source_bytes))
            conn.execute(
                "INSERT INTO imports (importer_file, imported_module, imported_names) VALUES (?,?,?)",
                (filepath, mod, ",".join(names) if names else None),
            )

        for child in n.children:
            walk(child)

    walk(root)


def _extract_symbols_and_calls(
    root, source_bytes: bytes, filepath: str, conn: sqlite3.Connection
):
    """Walk AST, insert symbols and their calls into the DB."""

    def walk_body(node, symbol_id: Optional[int], class_name: Optional[str], in_try: bool):
        """Recurse into nodes, tracking current function scope and try depth."""
        if node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            if name_node is None:
                return
            name = _node_text(name_node, source_bytes)
            body = node.child_by_field_name("body")
            complexity = _calculate_complexity(body) if body else 1
            loc = node.end_point[0] - node.start_point[0] + 1
            sym_type = "method" if class_name else "function"

            cur = conn.execute(
                "INSERT INTO symbols (name, type, file, line_start, line_end, complexity, loc, parent_class)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    name, sym_type, filepath,
                    node.start_point[0] + 1, node.end_point[0] + 1,
                    complexity, loc, class_name,
                ),
            )
            new_sym_id = cur.lastrowid

            # Walk children under this function's scope
            for child in node.children:
                walk_body(child, new_sym_id, class_name, False)
            return  # Don't fall through to generic child walk

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            cls_name = _node_text(name_node, source_bytes) if name_node else None
            loc = node.end_point[0] - node.start_point[0] + 1
            conn.execute(
                "INSERT INTO symbols (name, type, file, line_start, line_end, complexity, loc)"
                " VALUES (?,?,?,?,?,?,?)",
                (cls_name, "class", filepath, node.start_point[0] + 1, node.end_point[0] + 1, 1, loc),
            )
            for child in node.children:
                walk_body(child, symbol_id, cls_name, in_try)
            return

        if node.type == "try_statement":
            for child in node.children:
                walk_body(child, symbol_id, class_name, True)
            return

        if node.type == "call" and symbol_id is not None:
            callee_name, callee_full = _extract_call_name(node, source_bytes)
            if callee_name:
                conn.execute(
                    "INSERT INTO calls (caller_id, callee_name, callee_full, call_line, caller_file)"
                    " VALUES (?,?,?,?,?)",
                    (symbol_id, callee_name, callee_full, node.start_point[0] + 1, filepath),
                )

        for child in node.children:
            walk_body(child, symbol_id, class_name, in_try)

    walk_body(root, None, None, False)


def _index_file(
    source_bytes: bytes, filepath: str, conn: sqlite3.Connection
) -> None:
    if not TREE_SITTER_AVAILABLE or _py_parser is None:
        return

    tree = _py_parser.parse(source_bytes)
    root = tree.root_node

    _extract_imports(root, source_bytes, filepath, conn)
    _extract_symbols_and_calls(root, source_bytes, filepath, conn)


# ── Public API ────────────────────────────────────────────────────────────────

def index_project(
    source_root: str,
    db_path: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> IndexStats:
    """
    Index all supported files under source_root into the SQLite DB at db_path.
    Only re-indexes files whose MD5 hash has changed (incremental).
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = init_db(db_path)
    stats = IndexStats()

    # Load existing hashes for incremental indexing
    existing_hashes: dict[str, str] = {
        row[0]: row[1] for row in conn.execute("SELECT file, hash FROM file_meta")
    }

    # Discover files
    all_files: list[str] = []
    for root, dirs, files in os.walk(source_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for fname in files:
            fpath = os.path.join(root, fname)
            if Path(fpath).suffix.lower() in SUPPORTED_EXTENSIONS:
                if not _should_ignore(fpath, source_root):
                    all_files.append(fpath)

    total = len(all_files)

    for i, fpath in enumerate(all_files):
        rel_path = os.path.relpath(fpath, source_root).replace("\\", "/")
        current_hash = _file_hash(fpath)

        if progress_callback:
            pct = (i / total) if total else 1.0
            progress_callback(pct, f"Indexing {rel_path}")

        if existing_hashes.get(rel_path) == current_hash:
            continue  # unchanged

        try:
            source_bytes = Path(fpath).read_bytes()

            # Remove stale data
            conn.execute("DELETE FROM calls WHERE caller_file = ?", (rel_path,))
            conn.execute("DELETE FROM symbols WHERE file = ?", (rel_path,))
            conn.execute("DELETE FROM imports WHERE importer_file = ?", (rel_path,))

            _index_file(source_bytes, rel_path, conn)
            conn.execute(
                "INSERT OR REPLACE INTO file_meta (file, hash) VALUES (?,?)",
                (rel_path, current_hash),
            )
            stats.files_processed += 1

        except Exception as exc:
            print(f"Warning: could not index {fpath}: {exc}")

    conn.commit()

    row = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()
    stats.symbols_found = row[0] if row else 0
    row = conn.execute("SELECT COUNT(*) FROM calls").fetchone()
    stats.calls_found = row[0] if row else 0
    row = conn.execute("SELECT COUNT(*) FROM imports").fetchone()
    stats.imports_found = row[0] if row else 0

    conn.close()
    return stats
