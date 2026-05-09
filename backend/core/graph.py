"""
Query helpers over the SQLite call graph produced by indexer.py.
All functions accept a db_path string and return plain dicts.
"""
import sqlite3
from typing import Optional


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_symbols(db_path: str, file: Optional[str] = None) -> list[dict]:
    conn = _connect(db_path)
    if file:
        rows = conn.execute(
            "SELECT * FROM symbols WHERE file = ? ORDER BY file, line_start", (file,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM symbols ORDER BY file, line_start"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dead_code_candidates(db_path: str) -> list[dict]:
    """
    Functions/methods that are never called within the indexed codebase.
    Excludes: dunder methods, test functions, main, class definitions.
    """
    conn = _connect(db_path)
    rows = conn.execute(
        """
        SELECT s.id, s.name, s.type, s.file, s.line_start, s.line_end,
               s.complexity, s.loc, s.parent_class
        FROM symbols s
        WHERE s.type IN ('function', 'method')
          AND s.name NOT GLOB '__*__'
          AND s.name NOT LIKE 'test_%'
          AND s.name NOT LIKE 'Test%'
          AND s.name NOT IN ('main', 'setup', 'teardown', 'setUp', 'tearDown')
          AND s.name NOT IN (
              SELECT DISTINCT callee_name FROM calls
          )
        ORDER BY s.file, s.line_start
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complex_functions(db_path: str, threshold: int = 10) -> list[dict]:
    conn = _connect(db_path)
    rows = conn.execute(
        """
        SELECT id, name, type, file, line_start, line_end, complexity, loc, parent_class
        FROM symbols
        WHERE type IN ('function', 'method')
          AND complexity > ?
        ORDER BY complexity DESC
        """,
        (threshold,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_callers_of(db_path: str, function_name: str) -> list[dict]:
    """Which functions call the given function name?"""
    conn = _connect(db_path)
    rows = conn.execute(
        """
        SELECT s.id, s.name, s.file, s.line_start, c.call_line
        FROM calls c
        JOIN symbols s ON s.id = c.caller_id
        WHERE c.callee_name = ?
        ORDER BY s.file, c.call_line
        """,
        (function_name,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_callees_of(db_path: str, symbol_id: int) -> list[dict]:
    """Which functions does the given symbol call?"""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT callee_name, callee_full, call_line FROM calls WHERE caller_id = ?",
        (symbol_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_files(db_path: str) -> list[str]:
    conn = _connect(db_path)
    rows = conn.execute("SELECT DISTINCT file FROM symbols ORDER BY file").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_file_symbol_count(db_path: str) -> dict[str, int]:
    """Map of file → number of symbols (for heat-map)."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT file, COUNT(*) as cnt FROM symbols GROUP BY file ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_stats(db_path: str) -> dict:
    conn = _connect(db_path)
    stats = {
        "total_symbols": conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0],
        "total_functions": conn.execute(
            "SELECT COUNT(*) FROM symbols WHERE type IN ('function','method')"
        ).fetchone()[0],
        "total_calls": conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0],
        "total_files": conn.execute("SELECT COUNT(DISTINCT file) FROM symbols").fetchone()[0],
        "avg_complexity": conn.execute(
            "SELECT ROUND(AVG(complexity),2) FROM symbols WHERE type IN ('function','method')"
        ).fetchone()[0] or 0,
    }
    conn.close()
    return stats
