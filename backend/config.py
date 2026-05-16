import os

# When True: requires X-Anthropic-Api-Key header and enforces per-IP rate limits.
# Set to "true" only on the shared/public deployment (Render).
# Leave unset (defaults to False) for local dev or self-hosted instances.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COMPLEXITY_THRESHOLD = int(os.getenv("COMPLEXITY_THRESHOLD", "10"))
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85"))
MODEL_NAME = os.getenv("MODEL_NAME", "claude-haiku-4-5-20251001")

# ── Feature 1: Async engine ────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
AUDIT_TIMEOUT_SECONDS = int(os.getenv("AUDIT_TIMEOUT_SECONDS", "600"))
MAX_REPO_SIZE_MB = int(os.getenv("MAX_REPO_SIZE_MB", "200"))

# ── Analysis thresholds ────────────────────────────────────────────────────────
IGNORE_PATTERNS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".env", "dist", "build", ".debt-audit", ".tox", ".pytest_cache",
    ".mypy_cache", "coverage", ".coverage",
}

SUPPORTED_EXTENSIONS = {".py"}

SEVERITY_SCORES = {"critical": 4, "high": 3, "medium": 2, "low": 1}
EFFORT_SCORES = {"easy": 1, "medium": 2, "hard": 3}

EXTERNAL_CALL_PATTERNS = [
    "requests.",
    "httpx.",
    "subprocess.",
    "urllib.",
    "open(",
    ".execute(",
    ".query(",
    "socket.",
    "ftplib.",
    "smtplib.",
    "paramiko.",
]
