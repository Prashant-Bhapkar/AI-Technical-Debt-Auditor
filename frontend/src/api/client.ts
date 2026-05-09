const BASE = "/api";

export interface AuditStatus {
  audit_id: string;
  status: "queued" | "cloning" | "indexing" | "analyzing" | "done" | "error";
  progress: number;
  phase: string;
  error?: string;
}

export interface Finding {
  file: string;
  line: number;
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  why_it_matters: string;
  fix_suggestion: string;
  effort: "easy" | "medium" | "hard";
  priority_score: number;
  function_name: string;
}

export interface AuditSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_type: Record<string, number>;
  by_file: Record<string, number>;
}

export interface AuditResult {
  audit_id: string;
  score: number;
  findings: Finding[];
  summary: AuditSummary;
  graph_stats: Record<string, number | string>;
  source_path: string;
}

export interface RecentAudit {
  audit_id: string;
  status: string;
  progress: number;
  phase: string;
  source_path: string;
  score?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  startAudit: (body: { repo_url?: string; local_path?: string }) =>
    request<{ audit_id: string }>("/audit/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getStatus: (auditId: string) =>
    request<AuditStatus>(`/audit/status/${auditId}`),

  getResult: (auditId: string) =>
    request<AuditResult>(`/audit/result/${auditId}`),

  listAudits: () =>
    request<{ audits: RecentAudit[] }>("/audit/list"),
};
