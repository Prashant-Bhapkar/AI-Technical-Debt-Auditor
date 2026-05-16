"""Temporary directory lifecycle helpers for audit jobs."""
import os
import shutil
import tempfile
from contextlib import contextmanager


def make_temp_dir(prefix: str = "debt-audit-") -> str:
    """Create a temp dir and return its path. Caller is responsible for cleanup."""
    return tempfile.mkdtemp(prefix=prefix)


def cleanup(path: str | None) -> None:
    """Remove a directory tree if it exists. Silently ignores errors."""
    if path and os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


@contextmanager
def audit_temp_dir(prefix: str = "debt-audit-"):
    """Context manager: creates a temp dir and always cleans it up on exit."""
    path = make_temp_dir(prefix)
    try:
        yield path
    finally:
        cleanup(path)
