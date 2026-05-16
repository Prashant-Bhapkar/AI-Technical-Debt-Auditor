"""
Blueprint: /api/audit/*

POST /api/audit/start            { repo_url, checkers[] }  →  { audit_id }
GET  /api/audit/status/<id>      →  { status, progress, phase }
GET  /api/audit/result/<id>      →  full findings (only when done)
GET  /api/audit/list             →  recent audits

Dispatch strategy:
  • REDIS_URL configured  →  Celery async task  (V2)
  • No REDIS_URL          →  background thread  (V1 fallback)
"""
import logging
import tempfile
import threading
import time
import uuid

from flask import Blueprint, jsonify, request

from backend.core import audit_store
from backend.core.audit_runner import execute_audit, ALL_CHECKERS

log = logging.getLogger(__name__)
audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")


def get_audits_store():
    """Expose store proxy + lock to qa_routes / report_routes."""
    return audit_store.get_proxy()


def _clone_repo(url: str) -> tuple[str, str]:
    """Shallow-clone a GitHub repo. Returns (temp_dir, source_root)."""
    import git  # type: ignore
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

    user_api_key = request.headers.get("X-Anthropic-Api-Key", "").strip() or None
    requested_checkers = body.get("checkers")
    checkers: list[str] | None = (
        list(set(requested_checkers) & ALL_CHECKERS) if requested_checkers else None
    )

    audit_id = str(uuid.uuid4())
    temp_dir: str | None = None

    if repo_url:
        if "github.com" not in repo_url and not repo_url.startswith("http"):
            return jsonify(error="Invalid repo URL"), 400
        audit_store.store(audit_id, status="cloning", progress=2, phase="Cloning repository",
                          started_at=time.time())
        try:
            temp_dir, source_path = _clone_repo(repo_url)
        except Exception as exc:
            return jsonify(error=f"Clone failed: {exc}"), 400
    else:
        import os
        source_path = local_path
        if not os.path.isdir(source_path):
            return jsonify(error=f"Directory not found: {local_path}"), 400
        audit_store.store(audit_id, started_at=time.time())

    audit_store.store(audit_id, status="queued", progress=0, phase="Queued",
                      source_path=source_path)

    if audit_store.USING_REDIS:
        # V2: hand off to Celery worker
        from backend.worker.audit_job import run_audit  # lazy — only when Redis ready
        run_audit.delay(
            audit_id=audit_id,
            source_path=source_path,
            temp_dir=temp_dir,
            api_key=user_api_key,
            checkers=checkers,
        )
        log.info("Audit %s queued via Celery", audit_id)
    else:
        # V1 fallback: run in a daemon thread
        t = threading.Thread(
            target=execute_audit,
            args=(audit_id, source_path, temp_dir, user_api_key, checkers),
            daemon=True,
        )
        t.start()
        log.info("Audit %s started in thread (no Redis)", audit_id)

    return jsonify(audit_id=audit_id), 202


@audit_bp.get("/status/<audit_id>")
def get_status(audit_id: str):
    audit = audit_store.get(audit_id)
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
    audit = audit_store.get(audit_id)
    if not audit:
        return jsonify(error="Audit not found"), 404
    if audit.get("status") != "done":
        return jsonify(error="Audit not complete yet", status=audit.get("status")), 409
    result = audit.get("result", {})
    return jsonify(audit_id=audit_id, **result)


@audit_bp.get("/list")
def list_audits():
    items = [
        {
            "audit_id": aid,
            "status": data.get("status"),
            "progress": data.get("progress", 0),
            "phase": data.get("phase", ""),
            "source_path": data.get("source_path", ""),
            "score": data.get("result", {}).get("score"),
        }
        for aid, data in audit_store.all_audits()
    ]
    return jsonify(audits=items)
