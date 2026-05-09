import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Github, FolderOpen, Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { api, type AuditStatus, type RecentAudit } from "../api/client";
import clsx from "clsx";

const STATUS_ICONS: Record<string, React.ReactNode> = {
  done: <CheckCircle size={14} className="text-green-400" />,
  error: <XCircle size={14} className="text-red-400" />,
  indexing: <Loader2 size={14} className="text-blue-400 animate-spin" />,
  analyzing: <Loader2 size={14} className="text-purple-400 animate-spin" />,
  cloning: <Loader2 size={14} className="text-yellow-400 animate-spin" />,
  queued: <Clock size={14} className="text-gray-400" />,
};

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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startMutation = useMutation({
    mutationFn: (value: string) => {
      const isUrl = value.includes("github.com") || value.startsWith("http");
      return isUrl ? api.startAudit({ repo_url: value }) : api.startAudit({ local_path: value });
    },
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

  // Poll status while audit is running
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
    if (!input.trim() || isRunning) return;
    setActiveAuditId(null);
    startMutation.mutate(input.trim());
  };

  const isGithub = input.includes("github.com");

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 text-sky-400 text-sm font-medium bg-sky-900/30
                        border border-sky-800 px-3 py-1 rounded-full mb-4">
          <Search size={12} />
          AI-Powered Code Analysis
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
          Technical Debt Auditor
        </h1>
        <p className="text-gray-400 text-lg max-w-xl">
          Point it at any GitHub repo or local folder. Get a prioritized debt
          report with exact file + line references in seconds.
        </p>
      </div>

      {/* Input card */}
      <div className="w-full max-w-2xl bg-gray-800/60 border border-gray-700 rounded-2xl p-6 shadow-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              {isGithub ? <Github size={18} /> : <FolderOpen size={18} />}
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="https://github.com/owner/repo  or  C:\path\to\project"
              disabled={isRunning}
              className="w-full bg-gray-900/80 border border-gray-600 rounded-xl pl-10 pr-4 py-3
                         text-gray-100 placeholder-gray-500 text-sm focus:outline-none
                         focus:border-sky-500 focus:ring-1 focus:ring-sky-500
                         disabled:opacity-50 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isRunning}
            className="w-full bg-sky-600 hover:bg-sky-500 disabled:bg-gray-700 disabled:text-gray-500
                       text-white font-semibold py-3 rounded-xl transition-colors flex items-center
                       justify-center gap-2"
          >
            {isRunning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Auditing...
              </>
            ) : (
              <>
                <Search size={16} />
                Start Audit
              </>
            )}
          </button>
        </form>

        {/* Progress section */}
        {isRunning && statusData && (
          <div className="mt-6 space-y-3">
            <ProgressBar value={statusData.progress} label={statusData.phase} />
          </div>
        )}

        {/* Error */}
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

      {/* Feature bullets */}
      <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full text-sm text-gray-400">
        {[
          { icon: "🔍", title: "Dead Code", desc: "Find functions with zero callers via call graph" },
          { icon: "📊", title: "Complexity", desc: "Flag cyclomatic complexity over threshold" },
          { icon: "🛡️", title: "Error Handling", desc: "Detect unguarded I/O and network calls" },
        ].map((f) => (
          <div key={f.title} className="bg-gray-800/40 border border-gray-700 rounded-xl p-4">
            <div className="text-2xl mb-2">{f.icon}</div>
            <div className="font-semibold text-gray-200 mb-1">{f.title}</div>
            <div>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
