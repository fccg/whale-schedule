"use client";

interface TelemetryStatTileProps {
  label: string;
  value: string;
  hint?: string;
}

export default function TelemetryStatTile({ label, value, hint }: TelemetryStatTileProps) {
  return (
    <div className="rounded-2xl border border-white/8 bg-[#141414] p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-4 text-4xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-3 text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}
