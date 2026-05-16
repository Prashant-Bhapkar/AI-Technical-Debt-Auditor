"""
Blueprint: /api/audit/*

POST /api/audit/start            { repo_url, checkers[] }  →  { audit_id }
GET  /api/audit/status/<id>      →  { status, progress, phase }
GET  /api/audit/result/<id>      →  full findings (only when done)
GET  /api/audit/list             →  recent audits

Dispatch strategy (in priority order):
  1. X-Redis-Url header present  →  BYOR: per-request Redis + thread  (user's own Redis)
  2. Server REDIS_URL configured →  Celery async task                  (server Redis)
  3. No Redis at all             →  in-process background thread       (V1 fallback)

Security:
  - X-Anthropic-Api-Key header required — callers must supply their own key (403 otherwise)
  - Rate-limited to 2 audit starts per IP per day via Flask-Limiter
  - repo_url hostname must be github.com, gitlab.com, or bitbucket.org
"""
import logging
import tempfile
import threading
import time
import uuid
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from backend.config import DEMO_MODE
from backend.core import audit_store
from backend.core.audit_runner import execute_audit, ALL_CHECKERS
from backend.limiter import limiter

log = logging.getLogger(__name__)
audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")

ALLOWED_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


def get_audits_store():
    """Expose store proxy + lock to qa_routes / report_routes."""
    return audit_store.get_proxy()


def _validate_repo_url(url: str) -> str | None:
    """Return None if valid, or an error string if not."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "URL must use http:// or https://"
        if parsed.hostname not in ALLOWED_HOSTS:
            return "Only GitHub, GitLab, and Bitbucket repositories are supported"
        return None
    except Exception:
        return "Invalid URL format"


def _per_request_store(req):
    """
    Build a PerRequestStore from X-Redis-Url header, or return None.
    Logs a warning and returns None if the URL is invalid / unreachable.
    """
    url = req.headers.get("X-Redis-Url", "").strip()
    if not url:
        return None
    try:
        from backend.core.audit_store import PerRequestStore
        return PerRequestStore(url)
    except Exception as exc:
        log.warning("Per-request Redis connection failed (%s) — falling back to server store", exc)
        return None


def _read_audit(audit_id: str, per_store=None) -> dict | None:
    """Read audit state from per-request store if available, else global store."""
    if per_store is not None:
        return per_store.get_data(audit_id)
    return audit_store.get(audit_id)


def _clone_repo(url: str) -> tuple[str, str]:
    """Shallow-clone a repo. Returns (temp_dir, source_root)."""
    import git  # type: ignore
    temp_dir = tempfile.mkdtemp(prefix="debt-audit-")
    git.Repo.clone_from(url, temp_dir, depth=1)
    return temp_dir, temp_dir


# ── Routes ────────────────────────────────────────────────────────────────────

@audit_bp.post("/start")
@limiter.limit("2 per day", exempt_when=lambda: not DEMO_MODE)
def start_audit():
    body = request.get_json(silent=True) or {}
    repo_url = body.get("repo_url", "").strip()

    if not repo_url:
        return jsonify(error="repo_url is required"), 400

    user_api_key = request.headers.get("X-Anthropic-Api-Key", "").strip() or None

    url_error = _validate_repo_url(repo_url)
    if url_error:
        return jsonify(error=url_error), 400

    requested_checkers = body.get("checkers")
    checkers: list[str] | None = (
        list(set(requested_checkers) & ALL_CHECKERS) if requested_checkers else None
    )

    # ── Determine which state store to use ───────────────────────────────────
    per_store = _per_request_store(request)   # user's own Redis (BYOR)

    audit_id = str(uuid.uuid4())
    temp_dir: str | None = None

    def _init_store(**kwargs):
        if per_store:
            per_store.store_data(audit_id, **kwargs)
        else:
            audit_store.store(audit_id, **kwargs)

    _init_store(status="cloning", progress=2, phase="Cloning repository",
                started_at=time.time())
    try:
        temp_dir, source_path = _clone_repo(repo_url)
    except Exception as exc:
        return jsonify(error=f"Clone failed: {exc}"), 400

    _init_store(status="queued", progress=0, phase="Queued", source_path=source_path)

    # ── Dispatch ──────────────────────────────────────────────────────────────
    if per_store is not None:
        # BYOR Redis: thread mode with user's Redis as state store
        t = threading.Thread(
            target=execute_audit,
            kwargs=dict(audit_id=audit_id, source_path=source_path,
                        temp_dir=temp_dir, api_key=user_api_key,
                        checkers=checkers, state_store=per_store),
            daemon=True,
        )
        t.start()
        log.info("Audit %s started with user-provided Redis", audit_id)

    elif audit_store.USING_REDIS:
        # Server Redis: Celery async task
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
        # V1 fallback: in-process thread, in-memory store
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
    per_store = _per_request_store(request)
    audit = _read_audit(audit_id, per_store)
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
    per_store = _per_request_store(request)
    audit = _read_audit(audit_id, per_store)
    if not audit:
        return jsonify(error="Audit not found"), 404
    if audit.get("status") != "done":
        return jsonify(error="Audit not complete yet", status=audit.get("status")), 409
    result = audit.get("result", {})
    return jsonify(audit_id=audit_id, **result)


@audit_bp.get("/list")
def list_audits():
    # List always reads from the server store (per-user store has no list endpoint)
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
