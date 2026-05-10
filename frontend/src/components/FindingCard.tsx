import { useState } from "react";
import {
  ChevronDown, ChevronRight, FileCode, Wrench,
  AlertTriangle, Sparkles, Loader2,
} from "lucide-react";
import type { Finding, AIFix } from "../api/client";
import { api } from "../api/client";
import clsx from "clsx";

interface Props {
  finding: Finding;
  index: number;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-900/50 text-red-300 border-red-700",
  high:     "bg-orange-900/50 text-orange-300 border-orange-700",
  medium:   "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  low:      "bg-blue-900/50 text-blue-300 border-blue-700",
};

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-red-500",
  high:     "border-l-orange-500",
  medium:   "border-l-yellow-500",
  low:      "border-l-blue-500",
};

const TYPE_LABELS: Record<string, string> = {
  dead_code:        "Dead Code",
  complexity:       "Complexity",
  error_handling:   "Error Handling",
  duplicates:       "Duplicates",
  security:         "Security",
  observability:    "Observability",
  test_coverage:    "Test Coverage",
  outdated_patterns:"Outdated Patterns",
};

const EFFORT_STYLES: Record<string, string> = {
  easy:   "text-green-400",
  medium: "text-yellow-400",
  hard:   "text-red-400",
};

export default function FindingCard({ finding, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [aiFix, setAiFix] = useState<AIFix | null>(null);
  const [fixLoading, setFixLoading] = useState(false);
  const borderColor = SEVERITY_BORDER[finding.severity] ?? "border-l-gray-600";

  const handleGetFix = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (aiFix || fixLoading) return;
    setFixLoading(true);
    try {
      const fix = await api.getAIFix(finding);
      setAiFix(fix);
    } catch {
      setAiFix({ available: false, explanation: "Failed to get AI fix.", before: "", after: "", caveats: "" });
    } finally {
      setFixLoading(false);
    }
  };

  return (
    <div
      className={clsx(
        "bg-gray-800/60 border border-gray-700 border-l-4 rounded-lg overflow-hidden",
        borderColor
      )}
    >
      {/* Header row */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-gray-500 text-xs mt-0.5 w-5 shrink-0">{index + 1}</span>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className={clsx("text-xs font-semibold px-2 py-0.5 rounded border", SEVERITY_STYLES[finding.severity])}>
              {finding.severity.toUpperCase()}
            </span>
            <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
              {TYPE_LABELS[finding.type] ?? finding.type}
            </span>
            <span className={clsx("text-xs font-medium", EFFORT_STYLES[finding.effort])}>
              {finding.effort} fix
            </span>
            <span className="text-xs text-gray-500 ml-auto">score {finding.priority_score}</span>
          </div>
          <p className="text-sm text-gray-100 leading-snug">{finding.description}</p>
          <div className="flex items-center gap-1 mt-1.5 text-xs text-gray-400">
            <FileCode size={12} />
            <span className="font-mono">{finding.file}:{finding.line}</span>
          </div>
        </div>

        <div className="shrink-0 text-gray-500 mt-1">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-700/50">
          <div className="mt-3">
            <div className="flex items-center gap-1.5 text-xs text-amber-400 font-semibold mb-1">
              <AlertTriangle size={12} />
              Why it matters
            </div>
            <p className="text-sm text-gray-300">{finding.why_it_matters}</p>
          </div>

          <div>
            <div className="flex items-center gap-1.5 text-xs text-green-400 font-semibold mb-1">
              <Wrench size={12} />
              Fix suggestion
            </div>
            <p className="text-sm text-gray-300">{finding.fix_suggestion}</p>
          </div>

          {finding.function_name && (
            <p className="text-xs text-gray-500 font-mono">Function: {finding.function_name}</p>
          )}

          {/* AI Fix section */}
          {!aiFix && (
            <button
              onClick={handleGetFix}
              disabled={fixLoading}
              className="flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300
                         border border-sky-800 hover:border-sky-600 px-3 py-1.5 rounded-lg
                         transition-colors disabled:opacity-50"
            >
              {fixLoading ? (
                <><Loader2 size={12} className="animate-spin" /> Generating AI fix...</>
              ) : (
                <><Sparkles size={12} /> Get AI Fix</>
              )}
            </button>
          )}

          {aiFix && aiFix.available && (
            <div className="bg-gray-900/60 border border-gray-600 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-1.5 text-xs text-sky-400 font-semibold">
                <Sparkles size={12} />
                AI Fix
              </div>

              {aiFix.explanation && (
                <p className="text-sm text-gray-300">{aiFix.explanation}</p>
              )}

              {aiFix.before && (
                <div>
                  <div className="text-xs text-red-400 font-semibold mb-1">Before</div>
                  <pre className="text-xs text-gray-300 bg-red-900/20 border border-red-900/40
                                  rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {aiFix.before}
                  </pre>
                </div>
              )}

              {aiFix.after && (
                <div>
                  <div className="text-xs text-green-400 font-semibold mb-1">After</div>
                  <pre className="text-xs text-gray-300 bg-green-900/20 border border-green-900/40
                                  rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {aiFix.after}
                  </pre>
                </div>
              )}

              {aiFix.caveats && (
                <p className="text-xs text-amber-400 italic">{aiFix.caveats}</p>
              )}
            </div>
          )}

          {aiFix && !aiFix.available && (
            <p className="text-xs text-gray-500 italic">{aiFix.explanation}</p>
          )}
        </div>
      )}
    </div>
  );
}
