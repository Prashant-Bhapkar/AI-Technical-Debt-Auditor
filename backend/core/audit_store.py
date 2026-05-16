"""
Unified audit state store.

Uses Redis when REDIS_URL is configured (Celery/multi-process safe).
Falls back to an in-memory dict + threading.Lock for V1 compatibility.

Both audit_routes.py (Flask) and audit_job.py (Celery worker) import this
module so state is shared across processes via Redis.
"""
import json
import os
import threading
import time
from typing import Any

_redis_client = None
_audits: dict[str, dict] = {}
_lock = threading.Lock()
_TTL = 86400  # 24 hours

USING_REDIS = False


def init(redis_url: str | None = None) -> bool:
    """Connect to Redis. Returns True on success, False on fallback to memory."""
    global _redis_client, USING_REDIS
    url = redis_url or os.environ.get("REDIS_URL")
    if not url:
        return False
    try:
        import redis  # type: ignore
        r = redis.from_url(url, socket_connect_timeout=3, decode_responses=False)
        r.ping()
        _redis_client = r
        USING_REDIS = True
        print(f"[audit_store] Connected to Redis at {url}")
        return True
    except Exception as exc:
        print(f"[audit_store] Redis unavailable ({exc}), using in-memory store")
        return False


def store(audit_id: str, **kwargs: Any) -> None:
    """Upsert fields on an audit record."""
    if _redis_client is not None:
        key = f"audit:{audit_id}"
        raw = _redis_client.get(key)
        data: dict = json.loads(raw) if raw else {}
        data.update(kwargs)
        _redis_client.set(key, json.dumps(data), ex=_TTL)
    else:
        with _lock:
            _audits.setdefault(audit_id, {}).update(kwargs)


def get(audit_id: str) -> dict | None:
    """Return a copy of the audit record, or None if not found."""
    if _redis_client is not None:
        raw = _redis_client.get(f"audit:{audit_id}")
        return json.loads(raw) if raw else None
    else:
        with _lock:
            d = _audits.get(audit_id)
            return dict(d) if d is not None else None


def all_audits() -> list[tuple[str, dict]]:
    """Return all audit records as (audit_id, state) sorted newest-first."""
    if _redis_client is not None:
        results: list[tuple[str, dict]] = []
        for key in _redis_client.scan_iter("audit:*"):
            raw = _redis_client.get(key)
            if raw:
                audit_id = key.decode().removeprefix("audit:")
                results.append((audit_id, json.loads(raw)))
        results.sort(key=lambda x: x[1].get("started_at", 0), reverse=True)
        return results
    else:
        with _lock:
            items = list(_audits.items())
        return list(reversed([(aid, dict(d)) for aid, d in items]))


# ── Backward-compat proxy for qa_routes / report_routes ──────────────────────

class _RedisProxy:
    """Dict-like read proxy so qa_routes/report_routes work unchanged."""

    def get(self, audit_id: str, default: Any = None) -> Any:  # noqa: ANN401
        result = get(audit_id)
        return result if result is not None else default


class _DummyLock:
    """No-op context manager — Redis operations are already atomic."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def get_proxy() -> tuple[Any, Any]:
    """Return (store_proxy, lock) compatible with init_qa_routes / init_report_routes."""
    if USING_REDIS:
        return _RedisProxy(), _DummyLock()
    return _audits, _lock
