import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COMPLEXITY_THRESHOLD = int(os.getenv("COMPLEXITY_THRESHOLD", "10"))
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85"))
MODEL_NAME = os.getenv("MODEL_NAME", "claude-haiku-4-5-20251001")

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
