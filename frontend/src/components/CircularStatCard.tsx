"use client";

interface CircularStatCardProps {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  color?: string;
}

export default function CircularStatCard({ label, value, max = 100, unit = "%", color = "#8A5CF5" }: CircularStatCardProps) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="14" fill="none" stroke="oklch(0.269 0 0)" strokeWidth="4" />
          <circle cx="18" cy="18" r="14" fill="none" stroke={color} strokeWidth="4"
            strokeDasharray={`${(pct / 100) * 88} 88`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold">{value.toFixed(0)}{unit}</span>
        </div>
      </div>
      <span className="text-xs text-muted-foreground mt-2">{label}</span>
    </div>
  );
}
