"use client";

import { Button } from "@/components/ui/button";
import InstanceStatusBadge from "@/components/InstanceStatusBadge";
import type { GPUOffering, Instance, RuntimeInfo } from "@/lib/api";

interface InstanceHeroBarProps {
  instance: Instance;
  offering: GPUOffering | null;
  runtime: RuntimeInfo;
  onDestroy: () => void;
}

function formatUptime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

export default function InstanceHeroBar({ instance, offering, runtime, onDestroy }: InstanceHeroBarProps) {
  return (
    <div className="rounded-2xl border border-white/8 bg-[#141414] p-5">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <InstanceStatusBadge status={instance.status} />
            <span className="rounded-full bg-white/6 px-3 py-1 text-sm text-white">
              {(offering?.gpu_model || instance.gpu_offering_id) ?? "Unknown GPU"}
            </span>
            <span className="rounded-full bg-white/6 px-3 py-1 text-sm text-white">{instance.provider}</span>
          </div>
          <div>
            <h1 className="text-3xl font-semibold text-white">
              {offering?.gpu_count ?? 1}x {offering?.gpu_model ?? instance.gpu_offering_id}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {offering?.region ?? "Unknown region"} · Instance {instance.id.slice(0, 12)} · 最近心跳{" "}
              {instance.last_heartbeat_at ? new Date(instance.last_heartbeat_at).toLocaleTimeString("zh-CN") : "无"}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Uptime</p>
            <p className="text-xl font-semibold text-white">{formatUptime(runtime.uptime_seconds)}</p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Price</p>
            <p className="text-xl font-semibold text-white">¥{offering?.price_per_hour?.toFixed(2) ?? "--"}/h</p>
          </div>
          <Button variant="outline" className="border-white/12 bg-black/20 text-white hover:bg-white/10">
            OPEN
          </Button>
          <Button variant="destructive" onClick={onDestroy}>
            DESTROY
          </Button>
        </div>
      </div>
    </div>
  );
}
