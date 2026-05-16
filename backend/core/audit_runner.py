"""
Pure audit pipeline — no Celery dependency.

Called by:
  - backend/worker/audit_job.py  (Celery async path)
  - backend/routes/audit_routes.py  (V1 thread fallback when Redis unavailable)
"""
import logging
import os

from backend.core import audit_store, indexer, prioritizer, ai_analyzer, audit_history
from backend.core.checkers import (
    dead_code, complexity, error_handling,
    security, observability, test_coverage,
    outdated_patterns, duplicates,
)
from backend.core.graph import get_stats
from backend.core.temp_manager import cleanup

log = logging.getLogger(__name__)

ALL_CHECKERS: frozenset[str] = frozenset({
    "dead_code", "complexity", "error_handling",
    "security", "observability", "test_coverage",
    "outdated_patterns", "duplicates", "ai_insights",
})


def execute_audit(
    audit_id: str,
    source_path: str,
    temp_dir: str | None = None,
    api_key: str | None = None,
    checkers: list[str] | None = None,
    state_store=None,  # PerRequestStore | None — uses global audit_store when None
) -> None:
    """
    Run every enabled checker, prioritize findings, and write the result to
    audit_store. Cleans up temp_dir on exit regardless of success or failure.

    Parameters
    ----------
    audit_id    : Unique audit identifier (UUID string).
    source_path : Absolute path to the cloned / local repo.
    temp_dir    : Directory to delete after the audit (usually the clone root).
    api_key     : Optional Anthropic API key for AI insights.
    checkers    : List of checker IDs to run. None means all checkers.
    """
    run: frozenset[str] = frozenset(checkers) if checkers is not None else ALL_CHECKERS

    def _store(**kwargs) -> None:
        if state_store is not None:
            state_store.store_data(audit_id, **kwargs)
        else:
            audit_store.store(audit_id, **kwargs)

    try:
        _store(status="indexing", progress=5, phase="Setting up workspace")

        audit_dir = os.path.join(source_path, ".debt-audit")
        os.makedirs(audit_dir, exist_ok=True)
        db_path = os.path.join(audit_dir, "graph.db")

        def on_progress(pct: float, phase_msg: str) -> None:
            _store(progress=int(5 + pct * 20), phase=phase_msg)

        _store(status="indexing", progress=5, phase="Parsing source files")
        stats = indexer.index_project(source_path, db_path, on_progress)

        # ── Static checkers ───────────────────────────────────────────────────
        findings = []

        _CHECKER_STEPS = [
            ("dead_code",         28, "Checking dead code",             lambda: dead_code.check(db_path)),
            ("complexity",        36, "Checking cyclomatic complexity",  lambda: complexity.check(db_path)),
            ("error_handling",    44, "Checking error handling",         lambda: error_handling.check(db_path, source_path)),
            ("security",          52, "Checking security patterns",      lambda: security.check(db_path, source_path)),
            ("observability",     60, "Checking observability",          lambda: observability.check(db_path, source_path)),
            ("test_coverage",     66, "Checking test coverage",          lambda: test_coverage.check(db_path, source_path)),
            ("outdated_patterns", 72, "Checking outdated patterns",      lambda: outdated_patterns.check(db_path, source_path)),
            ("duplicates",        78, "Checking for duplicate code",     lambda: duplicates.check(db_path, source_path)),
        ]

        for checker_id, progress, phase, fn in _CHECKER_STEPS:
            if checker_id not in run:
                continue
            _store(status="analyzing", progress=progress, phase=phase)
            try:
                findings += fn()
            except Exception:
                log.exception("Checker %s failed (skipped)", checker_id)

        # ── Prioritize ────────────────────────────────────────────────────────
        _store(progress=84, phase="Prioritizing findings")
        findings = prioritizer.prioritize(findings)
        score = prioritizer.calculate_debt_score(findings)
        summary = prioritizer.build_summary(findings)
        graph_stats = get_stats(db_path)

        # ── AI insights (optional) ────────────────────────────────────────────
        ai_insights: dict = {
            "available": False,
            "summary": "",
            "top_issues": [],
            "recommended_steps": [],
            "architecture_notes": "",
        }
        if "ai_insights" in run:
            _store(progress=91, phase="Generating AI insights")
            try:
                ai_insights = ai_analyzer.generate_insights(findings, source_path, api_key=api_key)
            except Exception:
                log.exception("AI insights failed (skipped)")

        completed_result = {
            "score": score,
            "findings": [f.to_dict() for f in findings],
            "summary": summary,
            "graph_stats": graph_stats,
            "source_path": source_path,
            "ai_insights": ai_insights,
            "stats": {
                "files_processed": stats.files_processed,
                "symbols_found": stats.symbols_found,
                "calls_found": stats.calls_found,
            },
        }

        audit_history.save_audit(audit_id, source_path, completed_result)
        _store(status="done", progress=100, phase="Complete", result=completed_result)
        log.info("Audit %s complete — score %s, %s findings", audit_id, score, len(findings))

    except Exception as exc:
        import traceback
        log.exception("Audit %s failed", audit_id)
        _store(status="error", error=str(exc), traceback=traceback.format_exc())

    finally:
        cleanup(temp_dir)
