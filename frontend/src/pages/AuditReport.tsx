import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, Download, Filter, SortDesc, CheckCircle, FileText, TrendingUp,
} from "lucide-react";
import { api, type Finding, type AIInsights } from "../api/client";
import FindingCard from "../components/FindingCard";
import DebtScoreGauge from "../components/DebtScoreGauge";
import CategoryBreakdown from "../components/CategoryBreakdown";
import AIInsightsPanel from "../components/AIInsightsPanel";
import QAChat from "../components/QAChat";
import clsx from "clsx";

type SeverityFilter = "all" | "critical" | "high" | "medium" | "low";
type TypeFilter = "all" | string;
type Tab = "findings" | "ai";

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function StatBadge({
  label, count, colorClass,
}: { label: string; count: number; colorClass: string }) {
  return (
    <div className={clsx("rounded-xl border px-4 py-3 text-center", colorClass)}>
      <div className="text-2xl font-bold">{count}</div>
      <div className="text-xs opacity-70 mt-0.5 uppercase tracking-wide">{label}</div>
    </div>
  );
}

export default function AuditReport() {
  const { auditId } = useParams<{ auditId: string }>();
  const navigate = useNavigate();
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [activeTab, setActiveTab] = useState<Tab>("findings");

  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-result", auditId],
    queryFn: () => api.getResult(auditId!),
    enabled: !!auditId,
  });

  const allTypes = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set(data.findings.map((f) => f.type)));
  }, [data]);

  const filtered = useMemo<Finding[]>(() => {
    if (!data) return [];
    return data.findings
      .filter((f) => severityFilter === "all" || f.severity === severityFilter)
      .filter((f) => typeFilter === "all" || f.type === typeFilter);
  }, [data, severityFilter, typeFilter]);

  const handleDownloadJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `debt-audit-${auditId?.slice(0, 8)}.json`;
    a.click();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-400 animate-pulse">Loading report...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-red-400">{(error as Error)?.message ?? "Failed to load report"}</p>
        <button onClick={() => navigate("/")} className="text-sky-400 hover:underline text-sm">
          Go back home
        </button>
      </div>
    );
  }

  const { score, summary, findings, source_path, ai_insights } = data;

  return (
    <div className="min-h-screen max-w-6xl mx-auto px-4 py-8">
      {/* Nav bar */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors text-sm"
        >
          <ArrowLeft size={16} />
          New Audit
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/trends")}
            className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm border
                       border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            <TrendingUp size={14} />
            Trends
          </button>
          <a
            href={auditId ? api.downloadMarkdown(auditId) : "#"}
            className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm border
                       border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            <FileText size={14} />
            .md
          </a>
          <a
            href={auditId ? api.downloadHTML(auditId) : "#"}
            className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm border
                       border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            <FileText size={14} />
            .html
          </a>
          <button
            onClick={handleDownloadJSON}
            className="flex items-center gap-2 text-sky-400 hover:text-sky-300 text-sm border
                       border-sky-800 hover:border-sky-600 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Download size={14} />
            .json
          </button>
        </div>
      </div>

      {/* Title */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Audit Report</h1>
        {source_path && (
          <p className="text-sm text-gray-400 font-mono mt-1 truncate">{source_path}</p>
        )}
      </div>

      {/* Score + summary row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        <div className="md:col-span-1 bg-gray-800/60 border border-gray-700 rounded-2xl p-5 flex items-center justify-center">
          <DebtScoreGauge score={score} />
        </div>
        <div className="md:col-span-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatBadge
            label="Critical"
            count={summary.critical}
            colorClass="bg-red-900/30 border-red-800 text-red-300"
          />
          <StatBadge
            label="High"
            count={summary.high}
            colorClass="bg-orange-900/30 border-orange-800 text-orange-300"
          />
          <StatBadge
            label="Medium"
            count={summary.medium}
            colorClass="bg-yellow-900/30 border-yellow-800 text-yellow-300"
          />
          <StatBadge
            label="Low"
            count={summary.low}
            colorClass="bg-blue-900/30 border-blue-800 text-blue-300"
          />
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5">
          <CategoryBreakdown byType={summary.by_type} />
        </div>
        <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Codebase Stats</h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(data.graph_stats).map(([k, v]) => (
              <div key={k} className="bg-gray-700/40 rounded-lg p-3">
                <div className="text-lg font-bold text-white">{String(v)}</div>
                <div className="text-xs text-gray-400 capitalize">
                  {k.replace(/_/g, " ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 bg-gray-800/60 border border-gray-700 rounded-xl p-1 w-fit">
        {(["findings", "ai"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              "text-sm px-4 py-1.5 rounded-lg capitalize transition-colors",
              activeTab === tab
                ? "bg-sky-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            )}
          >
            {tab === "ai" ? "AI Insights & Q&A" : "Findings"}
          </button>
        ))}
      </div>

      {activeTab === "ai" && (
        <div className="space-y-4">
          {ai_insights && <AIInsightsPanel insights={ai_insights} />}
          {auditId && <QAChat auditId={auditId} />}
        </div>
      )}

      {activeTab === "findings" && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-5">
            <div className="flex items-center gap-1 text-xs text-gray-400 mr-2">
              <Filter size={12} />
              Severity:
            </div>
            {(["all", "critical", "high", "medium", "low"] as SeverityFilter[]).map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={clsx(
                  "text-xs px-3 py-1 rounded-full border transition-colors capitalize",
                  severityFilter === s
                    ? "bg-sky-600 border-sky-500 text-white"
                    : "border-gray-600 text-gray-400 hover:border-gray-400"
                )}
              >
                {s === "all" ? `All (${findings.length})` : s}
              </button>
            ))}

            {allTypes.length > 0 && (
              <>
                <div className="flex items-center gap-1 text-xs text-gray-400 mx-2">
                  <SortDesc size={12} />
                  Type:
                </div>
                <button
                  onClick={() => setTypeFilter("all")}
                  className={clsx(
                    "text-xs px-3 py-1 rounded-full border transition-colors",
                    typeFilter === "all"
                      ? "bg-sky-600 border-sky-500 text-white"
                      : "border-gray-600 text-gray-400 hover:border-gray-400"
                  )}
                >
                  All types
                </button>
                {allTypes.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTypeFilter(t)}
                    className={clsx(
                      "text-xs px-3 py-1 rounded-full border transition-colors capitalize",
                      typeFilter === t
                        ? "bg-sky-600 border-sky-500 text-white"
                        : "border-gray-600 text-gray-400 hover:border-gray-400"
                    )}
                  >
                    {t.replace(/_/g, " ")}
                  </button>
                ))}
              </>
            )}
          </div>

          {/* Findings count */}
          <p className="text-sm text-gray-400 mb-4">
            Showing {filtered.length} of {findings.length} findings, sorted by priority
          </p>

          {/* Findings list */}
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <CheckCircle size={40} className="mx-auto mb-3 text-green-500 opacity-50" />
              <p className="text-lg font-medium text-gray-300">No findings match this filter</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map((finding, i) => (
                <FindingCard key={`${finding.file}-${finding.line}-${i}`} finding={finding} index={i} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
