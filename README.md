# AI Technical Debt Auditor

Point it at any GitHub repository or local folder, and get a prioritized technical debt report with exact file + line references in seconds.

## What it detects (Week 1-2 scope)

| Checker | Method |
|---|---|
| **Dead Code** | Functions with 0 callers in the call graph (SQLite query) |
| **Cyclomatic Complexity** | AST branch counting via tree-sitter |
| **Missing Error Handling** | External I/O calls not wrapped in try/except (AST) |

## Tech Stack

- **Backend**: Python 3.11+ · Flask · tree-sitter · SQLite
- **Frontend**: React 18 · TypeScript · Tailwind CSS · Recharts · React Query

---

## Setup

### Backend

```bash
# From project root
pip install -r requirements.txt

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

---

## API

```
POST /api/audit/start         { repo_url } or { local_path }  → { audit_id }
GET  /api/audit/status/:id    → { status, progress, phase }
GET  /api/audit/result/:id    → { score, findings[], summary }
GET  /api/audit/list          → { audits[] }
GET  /api/health              → { status }
```

## Project Structure

```
debt-auditor/
├── backend/
│   ├── core/
│   │   ├── indexer.py          # tree-sitter → SQLite call graph
│   │   ├── graph.py            # call graph SQL queries
│   │   ├── prioritizer.py      # severity × effort → priority score
│   │   └── checkers/
│   │       ├── __init__.py     # Finding dataclass
│   │       ├── dead_code.py
│   │       ├── complexity.py
│   │       └── error_handling.py
│   ├── reporters/
│   │   └── json_report.py
│   ├── routes/
│   │   └── audit_routes.py
│   ├── app.py
│   └── config.py
├── frontend/
│   └── src/
│       ├── pages/Home.tsx
│       ├── pages/AuditReport.tsx
│       ├── components/
│       └── api/client.ts
├── run_backend.py
└── requirements.txt
```

## Adding a new checker (v2+)

1. Create `backend/core/checkers/my_checker.py`
2. Implement `check(db_path, ...) -> list[Finding]`
3. Import and call it in `backend/routes/audit_routes.py` inside `_run_audit`

No other files need to change.
