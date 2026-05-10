# Contributing to AI Technical Debt Auditor

Thank you for your interest in contributing! This document explains how to get started.

## Ways to Contribute

- **Bug reports** — open an issue with steps to reproduce
- **Feature requests** — open an issue describing the use case
- **New checkers** — the most impactful contribution (see below)
- **Language support** — extend indexer.py to support JS/TS, Java, Go, etc.
- **UI improvements** — React components in `frontend/src/`
- **Documentation** — improve setup guides or add examples

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Backend

```bash
git clone https://github.com/Prashant-Bhapkar/AI-Technical-Debt-Auditor.git
cd AI-Technical-Debt-Auditor

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

# Optional: set your Anthropic key for AI features
cp .env.example .env
# edit .env and add ANTHROPIC_API_KEY=sk-ant-...

python run_backend.py
# Flask runs on http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Vite dev server on http://localhost:3000
```

## Adding a New Checker

A checker is a single Python file that returns a list of `Finding` objects. This is the most common contribution.

1. Create `backend/core/checkers/my_checker.py`:

```python
from backend.core.checkers import Finding

def check(db_path: str, source_root: str) -> list[Finding]:
    findings = []
    # your logic here
    findings.append(Finding(
        file="path/to/file.py",
        line=42,
        type="my_checker",          # snake_case, shown in UI filters
        severity="high",            # critical | high | medium | low
        description="What is wrong",
        why_it_matters="Why this matters to the developer",
        fix_suggestion="How to fix it",
        effort="medium",            # easy | medium | hard
        function_name="my_func",
    ))
    return findings
```

2. Register it in `backend/routes/audit_routes.py`:
   - Add `from backend.core.checkers import my_checker` at the top
   - Add `"my_checker"` to the `_ALL_CHECKERS` set
   - Add the conditional call inside `_run_audit`

3. Add it to the `STATIC_CHECKERS` list in `frontend/src/pages/Home.tsx` with an icon and description.

That's it — no other files need to change.

## Pull Request Guidelines

- Keep PRs focused: one feature or fix per PR
- Add a brief description of what and why in the PR body
- If adding a checker, include an example repo that triggers it
- Run `npm run build` in `frontend/` to catch TypeScript errors before pushing

## Code Style

- **Python**: follow existing patterns, no formatter enforced yet
- **TypeScript/React**: follow existing component structure
- **No AI-generated commit messages** — write a real one-line summary

## Reporting Issues

Please include:
- What you did
- What you expected
- What actually happened
- The audit URL or repo you tested against (if applicable)
