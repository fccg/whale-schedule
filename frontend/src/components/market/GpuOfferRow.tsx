"use client";

import { useRouter } from "next/navigation";
import { ShieldCheck, ChevronRight } from "lucide-react";
import type { GPUOffering } from "@/lib/api";

interface GpuOfferRowProps {
  gpu: GPUOffering;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <p className="truncate text-sm text-white">{value}</p>
    </div>
  );
}

export default function GpuOfferRow({ gpu }: GpuOfferRowProps) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push(`/gpus/${gpu.id}/configure`)}
      className="grid w-full gap-4 rounded-2xl border border-white/8 bg-[#111111] px-5 py-4 text-left transition hover:border-[#8A5CF5]/60 hover:bg-[#151515]"
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/6 text-lg font-semibold text-white">
            {gpu.gpu_model.split(" ").pop()?.slice(0, 1) ?? "G"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-semibold text-white">
                {gpu.gpu_count}x {gpu.gpu_model}
              </h3>
              {gpu.verified && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  verified
                </span>
              )}
              {gpu.badge_tags.slice(0, 3).map((tag) => (
                <span key={tag} className="rounded-full bg-white/6 px-2 py-1 text-xs text-muted-foreground">
                  {tag}
                </span>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              {gpu.host_display_name} · {gpu.provider} · {gpu.region}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 self-start xl:self-center">
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Price</p>
            <p className="text-2xl font-semibold text-white">
              ¥{gpu.price_per_hour.toFixed(2)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">/hr</span>
            </p>
          </div>
          <div className="inline-flex items-center rounded-xl bg-[#8A5CF5] px-4 py-3 text-sm font-medium text-white">
            RENT
            <ChevronRight className="ml-2 h-4 w-4" />
          </div>
        </div>
      </div>

      <div className="grid gap-4 border-t border-white/6 pt-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <Metric label="VRAM" value={`${gpu.vram_gb} GB`} />
        <Metric label="CPU" value={`${gpu.cpu_cores} cores`} />
        <Metric label="RAM" value={`${gpu.memory_gb} GB`} />
        <Metric label="Disk" value={`${gpu.disk_gb} GB ${gpu.disk_type}`} />
        <Metric label="Net Up" value={`${gpu.network_up_mbps.toFixed(0)} Mbps`} />
        <Metric label="Net Down" value={`${gpu.network_down_mbps.toFixed(0)} Mbps`} />
        <Metric label="Reliability" value={`${gpu.reliability_score.toFixed(1)}%`} />
        <Metric label="Duration" value={`${gpu.max_duration_days} days`} />
      </div>
    </button>
  );
}
