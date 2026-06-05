"use client";

import type { RuntimeInfo } from "@/lib/api";

interface GpuTelemetryPanelProps {
  runtime: RuntimeInfo;
}

export default function GpuTelemetryPanel({ runtime }: GpuTelemetryPanelProps) {
  if (!runtime.gpus.length) {
    return (
      <div className="rounded-2xl border border-white/8 bg-[#141414] p-5">
        <p className="text-sm text-muted-foreground">GPU Telemetry</p>
        <p className="mt-3 text-sm text-muted-foreground">尚未收到 GPU 明细指标。</p>
      </div>
    );
  }

  const gpu = runtime.gpus[0];

  const fmt = (v: number | null | undefined, digits = 1) =>
    v != null ? v.toFixed(digits) : "--";

  return (
    <div className="rounded-2xl border border-white/8 bg-[#141414] p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">GPU 0</p>
          <h3 className="text-2xl font-semibold text-white">Accelerator Telemetry</h3>
        </div>
        <div className="rounded-full bg-white/6 px-3 py-1 text-sm text-white">P-State {runtime.pstate ?? "--"}</div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">VRAM</p>
          <p className="mt-3 text-3xl font-semibold text-white">{gpu.vram_percent != null ? `${gpu.vram_percent}%` : "--"}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {gpu.vram_used_gb != null ? gpu.vram_used_gb : "--"} / {gpu.vram_total_gb != null ? `${gpu.vram_total_gb} GB` : "--"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Utilization</p>
          <p className="mt-3 text-3xl font-semibold text-white">{gpu.utilization != null ? `${gpu.utilization}%` : "--"}</p>
          <p className="mt-2 text-sm text-muted-foreground">Current load</p>
        </div>
        <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Temp / Power</p>
          <p className="mt-3 text-3xl font-semibold text-white">{fmt(gpu.temp_c)}°C</p>
          <p className="mt-2 text-sm text-muted-foreground">{fmt(gpu.power_w)} W</p>
        </div>
        <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Driver / CUDA</p>
          <p className="mt-3 text-xl font-semibold text-white">{runtime.driver_version || "--"}</p>
          <p className="mt-2 text-sm text-muted-foreground">CUDA {runtime.cuda_version || "--"}</p>
        </div>
      </div>
    </div>
  );
}
