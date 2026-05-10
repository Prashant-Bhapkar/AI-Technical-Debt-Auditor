"""Generate a self-contained HTML audit report."""
from __future__ import annotations

from datetime import datetime, timezone

SEVERITY_COLORS = {
    "critical": ("#7f1d1d", "#fca5a5"),
    "high":     ("#7c2d12", "#fdba74"),
    "medium":   ("#713f12", "#fde68a"),
    "low":      ("#1e3a5f", "#93c5fd"),
}

TYPE_LABELS = {
    "dead_code": "Dead Code",
    "complexity": "Complexity",
    "error_handling": "Error Handling",
    "duplicates": "Duplicates",
    "security": "Security",
    "observability": "Observability",
    "test_coverage": "Test Coverage",
    "outdated_patterns": "Outdated Patterns",
}


def _score_color(score: int) -> str:
    if score >= 80:
        return "#16a34a"
    if score >= 60:
        return "#ca8a04"
    if score >= 40:
        return "#ea580c"
    return "#dc2626"


def _finding_row(f: dict, idx: int) -> str:
    sev = f.get("severity", "low")
    bg, fg = SEVERITY_COLORS.get(sev, ("#374151", "#d1d5db"))
    label = TYPE_LABELS.get(f.get("type", ""), f.get("type", ""))
    return f"""
    <tr>
      <td style="padding:10px 12px;color:#9ca3af;font-size:13px">{idx}</td>
      <td style="padding:10px 12px">
        <span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;
                     font-size:11px;font-weight:700;text-transform:uppercase">{sev}</span>
      </td>
      <td style="padding:10px 12px;font-size:12px;color:#d1d5db">{label}</td>
      <td style="padding:10px 12px;font-size:13px;color:#f3f4f6">{f.get('description','')}</td>
      <td style="padding:10px 12px;font-family:monospace;font-size:12px;color:#60a5fa">
        {f.get('file','')}:{f.get('line','')}
      </td>
      <td style="padding:10px 12px;font-size:12px;color:#9ca3af">{f.get('effort','')}</td>
    </tr>
    <tr style="background:#1f2937">
      <td colspan="6" style="padding:0 12px 12px 12px">
        <div style="font-size:12px;color:#fcd34d;margin-bottom:4px">Why it matters</div>
        <div style="font-size:13px;color:#d1d5db;margin-bottom:8px">{f.get('why_it_matters','')}</div>
        <div style="font-size:12px;color:#6ee7b7;margin-bottom:4px">Fix suggestion</div>
        <div style="font-size:13px;color:#d1d5db">{f.get('fix_suggestion','')}</div>
      </td>
    </tr>"""


def generate(result: dict, audit_id: str) -> str:
    score = result.get("score", 0)
    summary = result.get("summary", {})
    findings = result.get("findings", [])
    source_path = result.get("source_path", "")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    score_color = _score_color(score)

    by_type_rows = "".join(
        f'<tr><td style="padding:6px 12px;color:#d1d5db">{TYPE_LABELS.get(k,k)}</td>'
        f'<td style="padding:6px 12px;color:#60a5fa;font-weight:700">{v}</td></tr>'
        for k, v in sorted(result.get("summary", {}).get("by_type", {}).items(),
                           key=lambda x: -x[1])
    )

    finding_rows = "".join(_finding_row(f, i + 1) for i, f in enumerate(findings))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Debt Audit Report — {source_path}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #111827; color: #f3f4f6; font-family: system-ui, sans-serif; padding: 32px 16px; }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 24px; font-weight: 700; color: #f9fafb; margin-bottom: 4px; }}
  .meta {{ font-size: 13px; color: #6b7280; margin-bottom: 32px; font-family: monospace; }}
  .card {{ background: #1f2937; border: 1px solid #374151; border-radius: 12px;
           padding: 20px; margin-bottom: 20px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }}
  .stat {{ background: #111827; border-radius: 8px; padding: 14px; text-align: center; }}
  .stat-val {{ font-size: 28px; font-weight: 700; }}
  .stat-label {{ font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 11px; color: #9ca3af;
              text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #374151; }}
  tbody tr:hover {{ background: #263040; }}
  .score-circle {{ width: 80px; height: 80px; border-radius: 50%;
                   background: conic-gradient({score_color} {score * 3.6}deg, #374151 0deg);
                   display: flex; align-items: center; justify-content: center; }}
  .score-inner {{ width: 60px; height: 60px; border-radius: 50%; background: #1f2937;
                  display: flex; align-items: center; justify-content: center;
                  font-size: 18px; font-weight: 700; color: {score_color}; }}
  .header-row {{ display: flex; align-items: center; gap: 20px; margin-bottom: 24px; }}
  h2 {{ font-size: 14px; font-weight: 600; color: #9ca3af; margin-bottom: 12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header-row">
    <div class="score-circle"><div class="score-inner">{score}</div></div>
    <div>
      <h1>Technical Debt Report</h1>
      <div class="meta">{source_path or audit_id}<br>Generated {generated_at}</div>
    </div>
  </div>

  <div class="card">
    <h2>Summary</h2>
    <div class="stats-grid">
      <div class="stat"><div class="stat-val" style="color:#fca5a5">{summary.get('critical',0)}</div><div class="stat-label">Critical</div></div>
      <div class="stat"><div class="stat-val" style="color:#fdba74">{summary.get('high',0)}</div><div class="stat-label">High</div></div>
      <div class="stat"><div class="stat-val" style="color:#fde68a">{summary.get('medium',0)}</div><div class="stat-label">Medium</div></div>
      <div class="stat"><div class="stat-val" style="color:#93c5fd">{summary.get('low',0)}</div><div class="stat-label">Low</div></div>
      <div class="stat"><div class="stat-val" style="color:#f9fafb">{summary.get('total',0)}</div><div class="stat-label">Total</div></div>
    </div>
  </div>

  <div class="card">
    <h2>By Type</h2>
    <table><tbody>{by_type_rows}</tbody></table>
  </div>

  <div class="card">
    <h2>Findings ({len(findings)})</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>Severity</th><th>Type</th>
          <th>Description</th><th>Location</th><th>Effort</th>
        </tr>
      </thead>
      <tbody>{finding_rows}</tbody>
    </table>
  </div>
</div>
</body>
</html>"""
