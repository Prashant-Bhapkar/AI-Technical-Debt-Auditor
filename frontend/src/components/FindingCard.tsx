import { useState } from "react";
import { ChevronDown, ChevronRight, FileCode, Wrench, AlertTriangle } from "lucide-react";
import type { Finding } from "../api/client";
import clsx from "clsx";

interface Props {
  finding: Finding;
  index: number;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-900/50 text-red-300 border-red-700",
  high: "bg-orange-900/50 text-orange-300 border-orange-700",
  medium: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  low: "bg-blue-900/50 text-blue-300 border-blue-700",
};

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

const TYPE_LABELS: Record<string, string> = {
  dead_code: "Dead Code",
  complexity: "Complexity",
  error_handling: "Error Handling",
  duplicates: "Duplicates",
  security: "Security",
  observability: "Observability",
  test_coverage: "Test Coverage",
  outdated_patterns: "Outdated Patterns",
};

const EFFORT_STYLES: Record<string, string> = {
  easy: "text-green-400",
  medium: "text-yellow-400",
  hard: "text-red-400",
};

export default function FindingCard({ finding, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const borderColor = SEVERITY_BORDER[finding.severity] ?? "border-l-gray-600";

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
            <span
              className={clsx(
                "text-xs font-semibold px-2 py-0.5 rounded border",
                SEVERITY_STYLES[finding.severity]
              )}
            >
              {finding.severity.toUpperCase()}
            </span>
            <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded">
              {TYPE_LABELS[finding.type] ?? finding.type}
            </span>
            <span className={clsx("text-xs font-medium", EFFORT_STYLES[finding.effort])}>
              {finding.effort} fix
            </span>
            <span className="text-xs text-gray-500 ml-auto">
              score {finding.priority_score}
            </span>
          </div>
          <p className="text-sm text-gray-100 leading-snug">{finding.description}</p>
          <div className="flex items-center gap-1 mt-1.5 text-xs text-gray-400">
            <FileCode size={12} />
            <span className="font-mono">
              {finding.file}:{finding.line}
            </span>
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
            <p className="text-xs text-gray-500 font-mono">
              Function: {finding.function_name}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
