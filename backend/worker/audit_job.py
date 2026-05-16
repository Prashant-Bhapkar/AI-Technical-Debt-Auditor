"""
Celery task: asynchronous technical debt audit.

The audit logic lives in backend.core.audit_runner (no Celery dependency there).
This module is thin: it just wraps execute_audit as a registered Celery task.
"""
import logging

from backend.worker.celery_app import celery
from backend.core.audit_runner import execute_audit

log = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="audit_job.run_audit",
    max_retries=0,          # audits are not retried automatically
    acks_late=True,
)
def run_audit(
    self,
    audit_id: str,
    source_path: str,
    temp_dir: str | None = None,
    api_key: str | None = None,
    checkers: list[str] | None = None,
) -> None:
    """Celery entry-point. Delegates immediately to execute_audit."""
    log.info("Worker picked up audit %s", audit_id)
    execute_audit(
        audit_id=audit_id,
        source_path=source_path,
        temp_dir=temp_dir,
        api_key=api_key,
        checkers=checkers,
    )
