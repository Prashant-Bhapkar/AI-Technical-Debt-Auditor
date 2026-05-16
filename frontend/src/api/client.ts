const BASE = import.meta.env.VITE_API_URL
  ? `https://${import.meta.env.VITE_API_URL}/api`
  : "/api";

function _storedKey(): string {
  try { return localStorage.getItem("anthropic_api_key") ?? ""; }
  catch { return ""; }
}

function _storedRedisUrl(): string {
  try { return localStorage.getItem("user_redis_url") ?? ""; }
  catch { return ""; }
}

export function setApiKey(key: string): void {
  try {
    if (key) localStorage.setItem("anthropic_api_key", key);
    else localStorage.removeItem("anthropic_api_key");
  } catch { /* storage blocked */ }
}

export function getApiKey(): string { return _storedKey(); }

export function setRedisUrl(url: string): void {
  try {
    if (url) localStorage.setItem("user_redis_url", url);
    else localStorage.removeItem("user_redis_url");
  } catch { /* storage blocked */ }
}

export function getRedisUrl(): string { return _storedRedisUrl(); }

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

export interface AIInsights {
  available: boolean;
  summary: string;
  top_issues: string[];
  recommended_steps: string[];
  architecture_notes: string;
}

export interface AuditResult {
  audit_id: string;
  score: number;
  findings: Finding[];
  summary: AuditSummary;
  graph_stats: Record<string, number | string>;
  source_path: string;
  ai_insights?: AIInsights;
  stats?: {
    files_processed: number;
    symbols_found: number;
    calls_found: number;
  };
}

export interface AIFix {
  available: boolean;
  explanation: string;
  before: string;
  after: string;
  caveats: string;
}

export interface AuditHistoryEntry {
  audit_id: string;
  source_path: string;
  score: number;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_type: Record<string, number>;
  created_at: string;
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
  const key = _storedKey();
  const redisUrl = _storedRedisUrl();
  const baseHeaders: Record<string, string> = { "Content-Type": "application/json" };
  if (key) baseHeaders["X-Anthropic-Api-Key"] = key;
  if (redisUrl) baseHeaders["X-Redis-Url"] = redisUrl;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...baseHeaders, ...(init?.headers as Record<string, string> ?? {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  startAudit: (body: { repo_url: string; checkers?: string[] }) =>
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

  askQuestion: (auditId: string, question: string) =>
    request<{ answer: string }>("/qa/ask", {
      method: "POST",
      body: JSON.stringify({ audit_id: auditId, question }),
    }),

  getAIFix: (finding: Finding) =>
    request<AIFix>("/qa/fix", {
      method: "POST",
      body: JSON.stringify({ finding }),
    }),

  downloadHTML: (auditId: string) => `${BASE}/report/${auditId}/html`,
  downloadMarkdown: (auditId: string) => `${BASE}/report/${auditId}/markdown`,

  getHistory: () =>
    request<{ history: AuditHistoryEntry[] }>("/history"),
};
