import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface Props {
  byType: Record<string, number>;
}

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

const COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#0ea5e9", "#8b5cf6", "#ec4899", "#14b8a6"];

export default function CategoryBreakdown({ byType }: Props) {
  const data = Object.entries(byType)
    .map(([type, count]) => ({ name: TYPE_LABELS[type] ?? type, count }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) return null;

  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Findings by Category</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
          <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            width={110}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 6 }}
            labelStyle={{ color: "#f9fafb" }}
            itemStyle={{ color: "#9ca3af" }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
