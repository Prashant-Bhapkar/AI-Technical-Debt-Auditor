import { Lightbulb, CheckSquare, AlertCircle } from "lucide-react";
import type { AIInsights } from "../api/client";

interface Props {
  insights: AIInsights;
}

export default function AIInsightsPanel({ insights }: Props) {
  if (!insights.available) {
    return (
      <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5 text-sm text-gray-400">
        <Lightbulb size={16} className="inline mr-2 text-yellow-500" />
        AI insights unavailable — set{" "}
        <code className="text-yellow-300">ANTHROPIC_API_KEY</code> to enable.
      </div>
    );
  }

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5 space-y-5">
      <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
        <Lightbulb size={16} className="text-yellow-400" />
        AI Analysis
      </h3>

      {insights.summary && (
        <p className="text-sm text-gray-300 leading-relaxed">{insights.summary}</p>
      )}

      {insights.top_issues.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <AlertCircle size={12} className="text-red-400" />
            Top Issues
          </h4>
          <ul className="space-y-1">
            {insights.top_issues.map((issue, i) => (
              <li key={i} className="text-sm text-gray-300 flex gap-2">
                <span className="text-red-400 mt-0.5">•</span>
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {insights.recommended_steps.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <CheckSquare size={12} className="text-green-400" />
            Recommended Steps
          </h4>
          <ol className="space-y-1">
            {insights.recommended_steps.map((step, i) => (
              <li key={i} className="text-sm text-gray-300 flex gap-2">
                <span className="text-green-400 shrink-0 font-mono">{i + 1}.</span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {insights.architecture_notes && (
        <div className="border-t border-gray-700 pt-4">
          <p className="text-xs text-gray-400 italic">{insights.architecture_notes}</p>
        </div>
      )}
    </div>
  );
}
