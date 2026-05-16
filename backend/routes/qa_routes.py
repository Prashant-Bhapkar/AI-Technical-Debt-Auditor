"""
Blueprint: /api/qa/*

POST /api/qa/ask  — answer a free-form question about an audit
POST /api/qa/fix  — generate a before/after AI code fix for a finding
"""
from flask import Blueprint, jsonify, request

from backend.core import ai_analyzer
from backend.core.checkers import Finding

qa_bp = Blueprint("qa", __name__, url_prefix="/api/qa")

_audits_ref: dict | None = None
_lock_ref = None


def init_qa_routes(audits: dict, lock):
    global _audits_ref, _lock_ref
    _audits_ref = audits
    _lock_ref = lock


def _get_audit(audit_id: str) -> dict | None:
    # Try user-provided Redis first (BYOR)
    user_url = request.headers.get("X-Redis-Url", "").strip()
    if user_url:
        try:
            from backend.core.audit_store import PerRequestStore
            return PerRequestStore(user_url).get_data(audit_id)
        except Exception:
            pass
    # Fall back to global store
    if _audits_ref is None or _lock_ref is None:
        return None
    with _lock_ref:
        d = _audits_ref.get(audit_id, {})
        return dict(d) if d else None


def _reconstruct_findings(raw: list[dict]) -> list[Finding]:
    return [
        Finding(
            file=f.get("file", ""),
            line=f.get("line", 0),
            type=f.get("type", ""),
            severity=f.get("severity", "low"),
            description=f.get("description", ""),
            why_it_matters=f.get("why_it_matters", ""),
            fix_suggestion=f.get("fix_suggestion", ""),
            effort=f.get("effort", "medium"),
            priority_score=f.get("priority_score", 0.0),
            function_name=f.get("function_name", ""),
        )
        for f in raw
    ]


@qa_bp.post("/ask")
def ask():
    body = request.get_json(silent=True) or {}
    audit_id = body.get("audit_id", "").strip()
    question = body.get("question", "").strip()

    if not audit_id:
        return jsonify(error="audit_id is required"), 400
    if not question:
        return jsonify(error="question is required"), 400

    audit = _get_audit(audit_id)
    if not audit:
        return jsonify(error="Audit not found"), 404
    if audit.get("status") != "done":
        return jsonify(error="Audit not complete yet"), 409

    api_key = request.headers.get("X-Anthropic-Api-Key", "").strip() or None
    result = audit.get("result", {})
    findings = _reconstruct_findings(result.get("findings", []))
    answer = ai_analyzer.answer_question(question, findings, result.get("source_path", ""), api_key=api_key)
    return jsonify(answer=answer)


@qa_bp.post("/fix")
def get_fix():
    body = request.get_json(silent=True) or {}
    finding = body.get("finding")

    if not finding or not isinstance(finding, dict):
        return jsonify(error="finding object is required"), 400

    api_key = request.headers.get("X-Anthropic-Api-Key", "").strip() or None
    fix = ai_analyzer.generate_fix(finding, api_key=api_key)
    return jsonify(**fix)
