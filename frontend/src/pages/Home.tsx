import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Github, Clock, CheckCircle, XCircle, Loader2, TrendingUp, ChevronDown, ChevronUp, KeyRound } from "lucide-react";
import { api, type AuditStatus, type RecentAudit, getApiKey } from "../api/client";
import clsx from "clsx";

const STATUS_ICONS: Record<string, React.ReactNode> = {
  done: <CheckCircle size={14} className="text-green-400" />,
  error: <XCircle size={14} className="text-red-400" />,
  indexing: <Loader2 size={14} className="text-blue-400 animate-spin" />,
  analyzing: <Loader2 size={14} className="text-purple-400 animate-spin" />,
  cloning: <Loader2 size={14} className="text-yellow-400 animate-spin" />,
  queued: <Clock size={14} className="text-gray-400" />,
};

const STATIC_CHECKERS = [
  { id: "dead_code",         icon: "🔍", label: "Dead Code",         desc: "Functions with zero callers" },
  { id: "complexity",        icon: "📊", label: "Complexity",        desc: "Cyclomatic complexity spikes" },
  { id: "error_handling",    icon: "🛡️", label: "Error Handling",    desc: "Unguarded I/O & network calls" },
  { id: "security",          icon: "🔐", label: "Security",          desc: "Secrets, eval(), SQL injection" },
  { id: "observability",     icon: "📡", label: "Observability",     desc: "Functions missing logging" },
  { id: "test_coverage",     icon: "🧪", label: "Test Coverage",     desc: "Untested public functions" },
  { id: "outdated_patterns", icon: "⚠️", label: "Outdated Patterns", desc: "Deprecated Python patterns" },
  { id: "duplicates",        icon: "📋", label: "Duplicates",        desc: "Similar / copy-paste code" },
];

const AI_CHECKERS = [
  { id: "ai_insights", icon: "🤖", label: "AI Insights & Q&A", desc: "Architecture summary + chat — requires API key" },
];

const ALL_STATIC_IDS = new Set(STATIC_CHECKERS.map((c) => c.id));

function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-sky-500 to-blue-600 rounded-full transition-all duration-500"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

function RecentAuditRow({ audit, onClick }: { audit: RecentAudit; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={audit.status !== "done"}
      className="w-full flex items-center gap-3 p-3 rounded-lg bg-gray-800/50 hover:bg-gray-700/50
                 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-left"
    >
      <span className="shrink-0">{STATUS_ICONS[audit.status] ?? STATUS_ICONS["queued"]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate font-mono">{audit.source_path || audit.audit_id}</p>
        <p className="text-xs text-gray-500 capitalize">{audit.status} · {audit.phase}</p>
      </div>
      {audit.score != null && (
        <span className="shrink-0 text-sm font-bold text-sky-400">{audit.score}</span>
      )}
    </button>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [activeAuditId, setActiveAuditId] = useState<string | null>(null);
  const [selectedCheckers, setSelectedCheckers] = useState<Set<string>>(new Set(ALL_STATIC_IDS));
  const [showCheckers, setShowCheckers] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toggleChecker = (id: string) => {
    setSelectedCheckers((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const aiSelected = selectedCheckers.has("ai_insights");
  const hasApiKey = !!getApiKey();

  const startMutation = useMutation({
    mutationFn: ({ url, checkers }: { url: string; checkers: string[] }) =>
      api.startAudit({ repo_url: url, checkers }),
    onSuccess: (data) => setActiveAuditId(data.audit_id),
  });

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ["audit-status", activeAuditId],
    queryFn: () => api.getStatus(activeAuditId!),
    enabled: !!activeAuditId,
    refetchInterval: false,
  });

  const { data: recentData, refetch: refetchList } = useQuery({
    queryKey: ["audit-list"],
    queryFn: api.listAudits,
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (!activeAuditId) return;
    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(async () => {
      const { data } = await refetchStatus();
      const s = (data as AuditStatus | undefined)?.status;
      if (s === "done") {
        clearInterval(intervalRef.current!);
        refetchList();
        navigate(`/report/${activeAuditId}`);
      } else if (s === "error") {
        clearInterval(intervalRef.current!);
        refetchList();
      }
    }, 2000);

    return () => clearInterval(intervalRef.current!);
  }, [activeAuditId]);

  const isRunning = startMutation.isPending || (
    activeAuditId != null &&
    statusData?.status != null &&
    !["done", "error"].includes(statusData.status)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const url = input.trim();
    if (!url || isRunning) return;
    setActiveAuditId(null);
    startMutation.mutate({ url, checkers: Array.from(selectedCheckers) });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="inline-flex items-center gap-2 text-sky-400 text-sm font-medium bg-sky-900/30
                          border border-sky-800 px-3 py-1 rounded-full">
            <Search size={12} />
            AI-Powered Code Analysis
          </div>
          <button
            onClick={() => navigate("/trends")}
            className="inline-flex items-center gap-1.5 text-gray-400 hover:text-gray-200 text-sm
                       border border-gray-700 hover:border-gray-500 px-3 py-1 rounded-full transition-colors"
          >
            <TrendingUp size={12} />
            Trends
          </button>
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
          Technical Debt Auditor
        </h1>
        <p className="text-gray-400 text-lg max-w-xl">
          Point it at any public GitHub repo. Get a prioritized debt report
          with exact file + line references in seconds.
        </p>
      </div>

      {/* Input card */}
      <div className="w-full max-w-2xl bg-gray-800/60 border border-gray-700 rounded-2xl p-6 shadow-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* URL input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              <Github size={18} />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="https://github.com/owner/repo"
              disabled={isRunning}
              className="w-full bg-gray-900/80 border border-gray-600 rounded-xl pl-10 pr-4 py-3
                         text-gray-100 placeholder-gray-500 text-sm focus:outline-none
                         focus:border-sky-500 focus:ring-1 focus:ring-sky-500
                         disabled:opacity-50 transition-colors"
            />
          </div>

          {/* Checker selection toggle */}
          <button
            type="button"
            onClick={() => setShowCheckers((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
          >
            {showCheckers ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            Choose checks to run
            <span className="ml-1 text-sky-500">
              {selectedCheckers.size} / {STATIC_CHECKERS.length + AI_CHECKERS.length} selected
            </span>
          </button>

          {showCheckers && (
            <div className="space-y-3">
              {/* Static checkers */}
              <p className="text-xs text-gray-500 uppercase tracking-wider">Static Analysis — no API key needed</p>
              <div className="grid grid-cols-2 gap-2">
                {STATIC_CHECKERS.map((c) => {
                  const on = selectedCheckers.has(c.id);
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleChecker(c.id)}
                      className={clsx(
                        "flex items-start gap-2 p-2.5 rounded-lg border text-left transition-colors text-xs",
                        on
                          ? "bg-sky-900/30 border-sky-700 text-sky-200"
                          : "bg-gray-800/40 border-gray-700 text-gray-500 hover:border-gray-500"
                      )}
                    >
                      <span className="text-base leading-none mt-0.5">{c.icon}</span>
                      <div>
                        <div className="font-semibold">{c.label}</div>
                        <div className="opacity-70 mt-0.5">{c.desc}</div>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* AI checkers */}
              <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">AI Features — requires Anthropic API key</p>
              <div className="grid grid-cols-1 gap-2">
                {AI_CHECKERS.map((c) => {
                  const on = selectedCheckers.has(c.id);
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleChecker(c.id)}
                      className={clsx(
                        "flex items-start gap-2 p-2.5 rounded-lg border text-left transition-colors text-xs",
                        on
                          ? "bg-purple-900/30 border-purple-700 text-purple-200"
                          : "bg-gray-800/40 border-gray-700 text-gray-500 hover:border-gray-500"
                      )}
                    >
                      <span className="text-base leading-none mt-0.5">{c.icon}</span>
                      <div>
                        <div className="font-semibold">{c.label}</div>
                        <div className="opacity-70 mt-0.5">{c.desc}</div>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* API key warning */}
              {aiSelected && !hasApiKey && (
                <p className="text-xs text-amber-400 bg-amber-900/20 border border-amber-800 rounded-lg px-3 py-2">
                  AI Insights selected but no API key set. Add your Anthropic key in the bar at the top of the page.
                </p>
              )}
            </div>
          )}

          {/* API key gate */}
          {!hasApiKey && (
            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-900/20
                            border border-amber-800 rounded-lg px-3 py-2">
              <KeyRound size={13} className="shrink-0" />
              <span>
                An Anthropic API key is required to run audits.
                Click <strong>Settings</strong> in the top-right bar to add yours.
              </span>
            </div>
          )}

          <button
            type="submit"
            disabled={!input.trim() || isRunning || selectedCheckers.size === 0 || !hasApiKey}
            className="w-full bg-sky-600 hover:bg-sky-500 disabled:bg-gray-700 disabled:text-gray-500
                       text-white font-semibold py-3 rounded-xl transition-colors flex items-center
                       justify-center gap-2"
          >
            {isRunning ? (
              <><Loader2 size={16} className="animate-spin" />Auditing...</>
            ) : (
              <><Search size={16} />Start Audit</>
            )}
          </button>
        </form>

        {/* Progress */}
        {isRunning && statusData && (
          <div className="mt-6 space-y-3">
            <ProgressBar value={statusData.progress} label={statusData.phase} />
          </div>
        )}

        {/* Errors */}
        {startMutation.isError && (
          <p className="mt-4 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-lg p-3">
            {startMutation.error?.message}
          </p>
        )}
        {statusData?.status === "error" && statusData.error && (
          <p className="mt-4 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-lg p-3">
            Audit failed: {statusData.error}
          </p>
        )}
      </div>

      {/* Recent audits */}
      {recentData && recentData.audits.length > 0 && (
        <div className="w-full max-w-2xl mt-8">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Clock size={14} />
            Recent Audits
          </h2>
          <div className="space-y-2">
            {recentData.audits.slice(0, 5).map((a) => (
              <RecentAuditRow
                key={a.audit_id}
                audit={a}
                onClick={() => navigate(`/report/${a.audit_id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Feature grid — all 8 checkers + AI */}
      <div className="mt-16 w-full max-w-2xl">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-4 text-center">What gets analyzed</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm text-gray-400">
          {[
            { icon: "🔍", title: "Dead Code",         desc: "Zero-caller functions" },
            { icon: "📊", title: "Complexity",        desc: "Cyclomatic spikes" },
            { icon: "🛡️", title: "Error Handling",   desc: "Unguarded I/O calls" },
            { icon: "🔐", title: "Security",          desc: "Secrets & injections" },
            { icon: "📡", title: "Observability",     desc: "Missing logging" },
            { icon: "🧪", title: "Test Coverage",     desc: "Untested functions" },
            { icon: "⚠️", title: "Outdated Patterns", desc: "Deprecated patterns" },
            { icon: "📋", title: "Duplicates",        desc: "Copy-paste code" },
          ].map((f) => (
            <div key={f.title} className="bg-gray-800/40 border border-gray-700 rounded-xl p-3">
              <div className="text-xl mb-1">{f.icon}</div>
              <div className="font-semibold text-gray-200 text-xs mb-0.5">{f.title}</div>
              <div className="text-xs">{f.desc}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3">
          <div className="bg-purple-900/20 border border-purple-800 rounded-xl p-3 flex items-center gap-3 text-sm">
            <span className="text-xl">🤖</span>
            <div>
              <span className="font-semibold text-purple-300">AI Insights & Q&A</span>
              <span className="text-gray-400 ml-2 text-xs">Architecture analysis, root-cause chat, and before/after code fixes · Requires Anthropic API key</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
