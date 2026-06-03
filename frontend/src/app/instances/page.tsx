"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { Instance } from "@/lib/api";
import InstanceStatusBadge from "@/components/InstanceStatusBadge";

export default function InstancesPage() {
  const router = useRouter();
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await api.getInstances();
      setInstances(res.instances);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [router]);

  if (loading) return <div className="max-w-6xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-semibold">我的实例</h1>
          <p className="text-muted-foreground">查看运行状态、监控链路和测试结果</p>
        </div>
      </div>

      {instances.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">还没有任何实例</p>
          <button onClick={() => router.push("/")} className="text-[#8A5CF5] hover:underline">
            去 GPU 市场选购
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-white/8 bg-[#141414]">
          <div className="grid grid-cols-[1.6fr_1fr_1fr_0.8fr_1fr] gap-4 border-b border-white/8 px-5 py-4 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            <span>实例</span>
            <span>GPU / Provider</span>
            <span>最近心跳</span>
            <span>进度</span>
            <span>状态</span>
          </div>
          {instances.map((inst) => (
            <button
              key={inst.id}
              className="grid w-full grid-cols-[1.6fr_1fr_1fr_0.8fr_1fr] gap-4 border-b border-white/6 px-5 py-5 text-left transition last:border-b-0 hover:bg-white/[0.03]"
              onClick={() => router.push(`/instances/${inst.id}`)}
            >
              <div>
                <div className="mb-1 flex items-center gap-3">
                  <span className="font-mono text-sm text-white">{inst.id.slice(0, 8)}</span>
                  <span className="text-sm text-muted-foreground">{inst.provider_instance_id}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  创建于 {new Date(inst.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
              <div>
                <p className="text-sm text-white">{inst.offering?.gpu_model ?? inst.gpu_offering_id}</p>
                <p className="text-xs text-muted-foreground">{inst.offering?.provider ?? inst.provider}</p>
              </div>
              <div className="text-sm text-muted-foreground">
                {inst.last_heartbeat_at ? new Date(inst.last_heartbeat_at).toLocaleTimeString("zh-CN") : "尚未上报"}
              </div>
              <div className="text-sm font-semibold text-white">{Math.round(inst.progress_percent)}%</div>
              <div className="flex items-center justify-start">
                <InstanceStatusBadge status={inst.status} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
