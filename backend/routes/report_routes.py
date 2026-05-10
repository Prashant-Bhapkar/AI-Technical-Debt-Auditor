"""
Blueprint: /api/report/*

GET /api/report/<audit_id>/html      — download HTML report
GET /api/report/<audit_id>/markdown  — download Markdown report
GET /api/history                     — persistent audit history
"""
from flask import Blueprint, Response, jsonify

from backend.reporters import html_report, markdown_report
from backend.core import audit_history

report_bp = Blueprint("report", __name__, url_prefix="/api")

_audits_ref: dict | None = None
_lock_ref = None


def init_report_routes(audits: dict, lock):
    global _audits_ref, _lock_ref
    _audits_ref = audits
    _lock_ref = lock


def _get_result(audit_id: str) -> dict | None:
    if _audits_ref is None or _lock_ref is None:
        return None
    with _lock_ref:
        audit = _audits_ref.get(audit_id, {})
    if audit.get("status") != "done":
        return None
    return audit.get("result")


@report_bp.get("/report/<audit_id>/html")
def download_html(audit_id: str):
    result = _get_result(audit_id)
    if result is None:
        return jsonify(error="Audit not found or not complete"), 404
    html = html_report.generate(result, audit_id)
    filename = f"debt-audit-{audit_id[:8]}.html"
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@report_bp.get("/report/<audit_id>/markdown")
def download_markdown(audit_id: str):
    result = _get_result(audit_id)
    if result is None:
        return jsonify(error="Audit not found or not complete"), 404
    md = markdown_report.generate(result, audit_id)
    filename = f"debt-audit-{audit_id[:8]}.md"
    return Response(
        md,
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@report_bp.get("/history")
def get_history():
    return jsonify(history=audit_history.get_history())
