import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { ArrowLeft, TrendingUp, Calendar, AlertTriangle } from "lucide-react";
import { api, type AuditHistoryEntry } from "../api/client";
import clsx from "clsx";

function scoreColor(score: number) {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function shortPath(path: string) {
  const parts = path.replace(/\\/g, "/").split("/");
  return parts.slice(-2).join("/") || path;
}

export default function Trends() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ["history"],
    queryFn: api.getHistory,
  });

  const history = data?.history ?? [];

  // Recharts needs ascending order for the line chart
  const chartData = [...history]
    .reverse()
    .map((a) => ({
      date: formatDate(a.created_at),
      score: a.score,
      label: shortPath(a.source_path),
    }));

  return (
    <div className="min-h-screen max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors text-sm"
        >
          <ArrowLeft size={16} />
          Home
        </button>
        <span className="text-gray-600">/</span>
        <div className="flex items-center gap-2 text-white font-semibold">
          <TrendingUp size={18} className="text-sky-400" />
          Audit Trends
        </div>
      </div>

      {isLoading && (
        <div className="text-gray-400 animate-pulse text-center py-16">Loading history...</div>
      )}

      {error && (
        <div className="text-red-400 text-center py-16">Failed to load history.</div>
      )}

      {!isLoading && history.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <TrendingUp size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-lg text-gray-400">No audit history yet.</p>
          <p className="text-sm mt-1">Run your first audit from the home page.</p>
        </div>
      )}

      {history.length > 0 && (
        <>
          {/* Score over time chart */}
          <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5 mb-6">
            <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
              <TrendingUp size={14} className="text-sky-400" />
              Debt Score Over Time
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#374151" }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: 8,
                    color: "#f9fafb",
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`${v}/100`, "Score"]}
                />
                <ReferenceLine y={80} stroke="#16a34a" strokeDasharray="4 4" strokeOpacity={0.4} />
                <ReferenceLine y={60} stroke="#ca8a04" strokeDasharray="4 4" strokeOpacity={0.4} />
                <ReferenceLine y={40} stroke="#ea580c" strokeDasharray="4 4" strokeOpacity={0.4} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ fill: "#38bdf8", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* History table */}
          <div className="bg-gray-800/60 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center gap-2">
              <Calendar size={14} className="text-gray-400" />
              <span className="text-sm font-semibold text-gray-300">
                Audit History ({history.length})
              </span>
            </div>
            <div className="divide-y divide-gray-700/50">
              {history.map((entry: AuditHistoryEntry) => (
                <div
                  key={entry.audit_id}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-gray-700/30 transition-colors"
                >
                  <div className={clsx("text-2xl font-bold w-12 text-center shrink-0", scoreColor(entry.score))}>
                    {entry.score}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono text-gray-200 truncate">
                      {shortPath(entry.source_path)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">{formatDate(entry.created_at)}</p>
                  </div>

                  <div className="flex gap-3 shrink-0 text-xs">
                    <span className="text-red-400">{entry.critical}C</span>
                    <span className="text-orange-400">{entry.high}H</span>
                    <span className="text-yellow-400">{entry.medium}M</span>
                    <span className="text-blue-400">{entry.low}L</span>
                  </div>

                  <div className="text-xs text-gray-500 shrink-0 w-16 text-right">
                    {entry.total} total
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
