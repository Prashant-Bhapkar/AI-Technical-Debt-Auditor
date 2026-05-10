"""
Persistent audit history stored in ~/.debt-auditor/history.db (SQLite).
Tracks completed audits across sessions and projects.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> str:
    base = Path.home() / ".debt-auditor"
    base.mkdir(exist_ok=True)
    return str(base / "history.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_history (
            id          TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            score       INTEGER NOT NULL,
            total       INTEGER NOT NULL,
            critical    INTEGER NOT NULL,
            high        INTEGER NOT NULL,
            medium      INTEGER NOT NULL,
            low         INTEGER NOT NULL,
            by_type     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_audit(audit_id: str, source_path: str, result: dict) -> None:
    summary = result.get("summary", {})
    conn = _connect()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO audit_history
               (id, source_path, score, total, critical, high, medium, low, by_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                source_path,
                result.get("score", 0),
                summary.get("total", 0),
                summary.get("critical", 0),
                summary.get("high", 0),
                summary.get("medium", 0),
                summary.get("low", 0),
                json.dumps(summary.get("by_type", {})),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_history(limit: int = 100) -> list[dict]:
    try:
        conn = _connect()
        rows = conn.execute(
            """SELECT id, source_path, score, total, critical, high, medium, low, by_type, created_at
               FROM audit_history
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {
                "audit_id": r[0],
                "source_path": r[1],
                "score": r[2],
                "total": r[3],
                "critical": r[4],
                "high": r[5],
                "medium": r[6],
                "low": r[7],
                "by_type": json.loads(r[8]),
                "created_at": r[9],
            }
            for r in rows
        ]
    except Exception:
        return []
