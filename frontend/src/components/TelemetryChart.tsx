"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface TelemetryChartProps {
  data: Array<{
    timestamp: string;
    cpu_percent?: number;
    memory_percent?: number;
    gpu_util_percent?: number;
    gpu_vram_percent?: number;
  }>;
  lines?: Array<{ key: string; name: string; color: string }>;
  height?: number;
}

const DEFAULT_LINES = [
  { key: "cpu_percent", name: "CPU", color: "#8A5CF5" },
  { key: "memory_percent", name: "Memory", color: "#60A5FA" },
  { key: "gpu_util_percent", name: "GPU", color: "#34D399" },
  { key: "gpu_vram_percent", name: "VRAM", color: "#F472B6" },
];

export default function TelemetryChart({ data, lines = DEFAULT_LINES, height = 300 }: TelemetryChartProps) {
  if (!data || data.length === 0) {
    return <p className="text-muted-foreground text-sm">暂无监控数据</p>;
  }
  const formatted = data.map((d) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.269 0 0)" />
        <XAxis dataKey="time" stroke="oklch(0.55 0 0)" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 100]} stroke="oklch(0.55 0 0)" tick={{ fontSize: 12 }} unit="%" />
        <Tooltip
          contentStyle={{ background: "oklch(0.22 0 0)", border: "1px solid oklch(0.35 0 0)", borderRadius: "8px" }}
          labelStyle={{ color: "oklch(0.8 0 0)" }}
        />
        <Legend />
        {lines.map((line) => (
          <Line key={line.key} type="monotone" dataKey={line.key} name={line.name}
            stroke={line.color} strokeWidth={2} dot={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
