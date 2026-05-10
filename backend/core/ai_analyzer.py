"""
Anthropic API integration for AI-powered analysis.

  generate_insights(findings, source_root) -> dict
    Summarises findings into actionable architecture insights.

  answer_question(question, findings, source_root) -> str
    Answers a free-form Q&A question about the codebase.

  generate_fix(finding_dict) -> dict
    Produces a before/after code fix for a specific finding.

All functions degrade gracefully when ANTHROPIC_API_KEY is not set.
"""
from __future__ import annotations

import json
import os
from typing import Any

from backend.config import ANTHROPIC_API_KEY, MODEL_NAME
from backend.core.checkers import Finding


def _client(api_key: str | None = None):
    key = api_key or ANTHROPIC_API_KEY
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        return None


def _findings_summary_text(findings: list[Finding], max_findings: int = 30) -> str:
    lines = []
    for f in findings[:max_findings]:
        lines.append(
            f"[{f.severity.upper()}] {f.type} | {f.file}:{f.line} | {f.description}"
        )
    if len(findings) > max_findings:
        lines.append(f"... and {len(findings) - max_findings} more findings")
    return "\n".join(lines)


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


# ── Insights ──────────────────────────────────────────────────────────────────

def generate_insights(findings: list[Finding], source_root: str, api_key: str | None = None) -> dict[str, Any]:
    """Return architecture-level insights from the full findings list."""
    empty = {
        "available": False,
        "summary": "",
        "top_issues": [],
        "recommended_steps": [],
        "architecture_notes": "",
    }

    client = _client(api_key)
    if not client or not findings:
        return empty

    by_type: dict[str, int] = {}
    for f in findings:
        by_type[f.type] = by_type.get(f.type, 0) + 1

    prompt = f"""You are a senior software architect reviewing technical debt findings.

Codebase: {source_root}
Total findings: {len(findings)}
Breakdown by type: {json.dumps(by_type)}

Top findings:
{_findings_summary_text(findings)}

Return a JSON object with exactly these keys:
{{
  "summary": "2-3 sentence executive summary",
  "top_issues": ["issue1", "issue2", "issue3"],
  "recommended_steps": ["step1", "step2", "step3"],
  "architecture_notes": "1-2 sentences on structural patterns observed"
}}

Be specific and reference actual finding types. Return only valid JSON."""

    try:
        resp = client.messages.create(
            model=MODEL_NAME,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(_strip_fences(resp.content[0].text))
        data["available"] = True
        return data
    except Exception as exc:
        print(f"Warning: AI insights failed: {exc}")
        return empty


# ── Q&A ───────────────────────────────────────────────────────────────────────

def answer_question(
    question: str,
    findings: list[Finding],
    source_root: str,
    api_key: str | None = None,
) -> str:
    client = _client(api_key)
    if not client:
        return (
            "AI Q&A is not available — set the ANTHROPIC_API_KEY environment "
            "variable and restart the server."
        )

    prompt = f"""You are a senior software engineer helping a developer understand technical debt.

Codebase: {source_root}
Technical debt findings ({len(findings)} total):
{_findings_summary_text(findings, max_findings=40)}

Developer question: {question}

Answer concisely and technically. Reference specific files or finding types where relevant.
If the question cannot be answered from the findings, say so clearly."""

    try:
        resp = client.messages.create(
            model=MODEL_NAME,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as exc:
        return f"Error generating answer: {exc}"


# ── Per-finding AI fix ────────────────────────────────────────────────────────

def generate_fix(finding: dict, api_key: str | None = None) -> dict[str, Any]:
    """
    Generate a concrete before/after code fix for a single finding.

    Returns:
      { available, explanation, before, after, caveats }
    """
    empty = {"available": False, "explanation": "", "before": "", "after": "", "caveats": ""}

    client = _client(api_key)
    if not client:
        return empty

    ftype = finding.get("type", "")
    fname = finding.get("function_name", "<module>")

    prompt = f"""You are a senior Python engineer. Fix the following technical debt finding.

File: {finding.get('file')}:{finding.get('line')}
Function: {fname}
Type: {ftype}
Severity: {finding.get('severity')}
Issue: {finding.get('description')}
Why it matters: {finding.get('why_it_matters')}
Current fix hint: {finding.get('fix_suggestion')}

Return a JSON object with exactly these keys:
{{
  "explanation": "2-3 sentences explaining the root cause and fix approach",
  "before": "realistic Python code snippet showing the problem (5-15 lines)",
  "after": "corrected Python code snippet (5-15 lines)",
  "caveats": "edge cases or things to watch for (1-2 sentences, or empty string)"
}}

Make the before/after snippets realistic and directly relevant to the finding type ({ftype}).
Do not include line numbers. Return only valid JSON."""

    try:
        resp = client.messages.create(
            model=MODEL_NAME,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(_strip_fences(resp.content[0].text))
        data["available"] = True
        return data
    except Exception as exc:
        print(f"Warning: AI fix generation failed: {exc}")
        return {**empty, "explanation": f"Could not generate fix: {exc}"}
