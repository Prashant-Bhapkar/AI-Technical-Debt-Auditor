"""
Celery application factory.

Environment variables (all optional — sensible defaults for local dev):
  REDIS_URL              Shared Redis URL (used as fallback for broker + backend)
  CELERY_BROKER_URL      Override broker URL  (default: REDIS_URL or redis://localhost:6379/0)
  CELERY_RESULT_BACKEND  Override backend URL (default: REDIS_URL or redis://localhost:6379/0)
  AUDIT_TIMEOUT_SECONDS  Hard timeout per audit task (default: 600)
"""
import os
from pathlib import Path

# Load .env so REDIS_URL etc. are available when the worker starts directly
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

from celery import Celery  # type: ignore

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
BROKER = os.environ.get("CELERY_BROKER_URL", _REDIS_URL)
BACKEND = os.environ.get("CELERY_RESULT_BACKEND", _REDIS_URL)
_TIMEOUT = int(os.environ.get("AUDIT_TIMEOUT_SECONDS", "600"))

celery = Celery(
    "debt_auditor",
    broker=BROKER,
    backend=BACKEND,
    include=["backend.worker.audit_job"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Reliability settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,   # one audit at a time per worker process
    # Timeouts: soft limit logs a warning, hard limit kills the task
    task_soft_time_limit=_TIMEOUT,
    task_time_limit=_TIMEOUT + 60,
    # Keep results for 24 h
    result_expires=86400,
)
