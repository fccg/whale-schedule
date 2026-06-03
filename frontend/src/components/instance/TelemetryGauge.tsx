"use client";

import { Pie, PieChart, ResponsiveContainer, Cell } from "recharts";

interface TelemetryGaugeProps {
  label: string;
  value: number | null | undefined;
  sublabel?: string;
  color?: string;
}

export default function TelemetryGauge({
  label,
  value,
  sublabel,
  color = "#8A5CF5",
}: TelemetryGaugeProps) {
  const safeValue = Math.max(0, Math.min(value ?? 0, 100));
  const data = [
    { name: "value", value: safeValue },
    { name: "rest", value: 100 - safeValue },
  ];

  return (
    <div className="rounded-2xl border border-white/8 bg-[#141414] p-5">
      <p className="mb-4 text-sm text-muted-foreground">{label}</p>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              startAngle={200}
              endAngle={-20}
              innerRadius={58}
              outerRadius={76}
              stroke="none"
              paddingAngle={0}
            >
              <Cell fill={color} />
              <Cell fill="rgba(255,255,255,0.08)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="-mt-24 text-center">
        <p className="text-4xl font-semibold text-white">{Math.round(safeValue)}%</p>
        {sublabel && <p className="mt-2 text-sm text-muted-foreground">{sublabel}</p>}
      </div>
    </div>
  );
}
