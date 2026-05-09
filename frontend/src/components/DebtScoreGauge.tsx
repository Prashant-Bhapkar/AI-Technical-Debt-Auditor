import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";

interface Props {
  score: number;
}

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Healthy";
  if (score >= 60) return "Moderate";
  if (score >= 40) return "Concerning";
  return "Critical";
}

export default function DebtScoreGauge({ score }: Props) {
  const color = scoreColor(score);
  const data = [{ value: score, fill: color }];

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <RadialBarChart
          width={180}
          height={180}
          cx={90}
          cy={90}
          innerRadius={60}
          outerRadius={85}
          barSize={14}
          data={data}
          startAngle={210}
          endAngle={-30}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "#1f2937" }} />
        </RadialBarChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold" style={{ color }}>
            {score}
          </span>
          <span className="text-xs text-gray-400 mt-0.5">/ 100</span>
        </div>
      </div>
      <span className="mt-1 text-sm font-semibold" style={{ color }}>
        {scoreLabel(score)}
      </span>
      <span className="text-xs text-gray-500">Debt Score</span>
    </div>
  );
}
