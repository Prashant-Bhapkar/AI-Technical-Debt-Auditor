"""
Blueprint: /api/audit/*

POST /api/audit/start  — start a new audit (background thread)
GET  /api/audit/status/<audit_id>  — current progress
GET  /api/audit/result/<audit_id>  — full findings (only when done)
GET  /api/audit/list               — recent audits
"""
import os
import shutil
import sqlite3
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.core import indexer
from backend.core import prioritizer
from backend.core.checkers import dead_code, complexity, error_handling
from backend.core.graph import get_stats

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")

# In-memory store: { audit_id: { status, progress, phase, result?, error? } }
_audits: dict[str, dict] = {}
_lock = threading.Lock()


def _store(audit_id: str, **kwargs):
    with _lock:
        _audits.setdefault(audit_id, {}).update(kwargs)


def _get(audit_id: str) -> dict | None:
    with _lock:
        return dict(_audits.get(audit_id, {}))


# ── Background worker ─────────────────────────────────────────────────────────

def _run_audit(audit_id: str, source_path: str, temp_dir: str | None = None):
    try:
        _store(audit_id, status="indexing", progress=5, phase="Setting up workspace")

        audit_dir = os.path.join(source_path, ".debt-audit")
        os.makedirs(audit_dir, exist_ok=True)
        db_path = os.path.join(audit_dir, "graph.db")

        def on_progress(pct: float, phase_msg: str):
            _store(
                audit_id,
                progress=int(10 + pct * 30),
                phase=phase_msg,
            )

        _store(audit_id, status="indexing", progress=10, phase="Parsing source files")
        stats = indexer.index_project(source_path, db_path, on_progress)

        _store(audit_id, status="analyzing", progress=42, phase="Checking dead code")
        findings = dead_code.check(db_path)

        _store(audit_id, progress=58, phase="Checking cyclomatic complexity")
        findings += complexity.check(db_path)

        _store(audit_id, progress=72, phase="Checking error handling")
        findings += error_handling.check(db_path, source_path)

        _store(audit_id, progress=85, phase="Prioritizing findings")
        findings = prioritizer.prioritize(findings)
        score = prioritizer.calculate_debt_score(findings)
        summary = prioritizer.build_summary(findings)
        graph_stats = get_stats(db_path)

        _store(
            audit_id,
            status="done",
            progress=100,
            phase="Complete",
            result={
                "score": score,
                "findings": [f.to_dict() for f in findings],
                "summary": summary,
                "graph_stats": graph_stats,
                "source_path": source_path,
            },
        )

    except Exception as exc:
        import traceback
        _store(audit_id, status="error", error=str(exc), traceback=traceback.format_exc())

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def _clone_repo(url: str) -> tuple[str, str]:
    """Clone GitHub repo; returns (temp_dir, source_root)."""
    import git
    temp_dir = tempfile.mkdtemp(prefix="debt-audit-")
    git.Repo.clone_from(url, temp_dir, depth=1)
    return temp_dir, temp_dir


# ── Routes ────────────────────────────────────────────────────────────────────

@audit_bp.post("/start")
def start_audit():
    body = request.get_json(silent=True) or {}
    repo_url = body.get("repo_url", "").strip()
    local_path = body.get("local_path", "").strip()

    if not repo_url and not local_path:
        return jsonify(error="Provide repo_url or local_path"), 400

    audit_id = str(uuid.uuid4())
    temp_dir = None

    if repo_url:
        if "github.com" not in repo_url and not repo_url.startswith("http"):
            return jsonify(error="Invalid repo URL"), 400
        _store(audit_id, status="cloning", progress=2, phase="Cloning repository")
        try:
            temp_dir, source_path = _clone_repo(repo_url)
        except Exception as exc:
            return jsonify(error=f"Clone failed: {exc}"), 400
    else:
        source_path = local_path
        if not os.path.isdir(source_path):
            return jsonify(error=f"Directory not found: {source_path}"), 400

    _store(audit_id, status="queued", progress=0, phase="Queued", source_path=source_path)

    t = threading.Thread(
        target=_run_audit, args=(audit_id, source_path, temp_dir), daemon=True
    )
    t.start()

    return jsonify(audit_id=audit_id), 202


@audit_bp.get("/status/<audit_id>")
def get_status(audit_id: str):
    audit = _get(audit_id)
    if not audit:
        return jsonify(error="Audit not found"), 404
    return jsonify(
        audit_id=audit_id,
        status=audit.get("status"),
        progress=audit.get("progress", 0),
        phase=audit.get("phase", ""),
        error=audit.get("error"),
    )


@audit_bp.get("/result/<audit_id>")
def get_result(audit_id: str):
    audit = _get(audit_id)
    if not audit:
        return jsonify(error="Audit not found"), 404
    if audit.get("status") != "done":
        return jsonify(error="Audit not complete yet", status=audit.get("status")), 409
    result = audit.get("result", {})
    return jsonify(audit_id=audit_id, **result)


@audit_bp.get("/list")
def list_audits():
    with _lock:
        items = [
            {
                "audit_id": aid,
                "status": data.get("status"),
                "progress": data.get("progress", 0),
                "phase": data.get("phase", ""),
                "source_path": data.get("source_path", ""),
                "score": data.get("result", {}).get("score"),
            }
            for aid, data in _audits.items()
        ]
    return jsonify(audits=list(reversed(items)))
