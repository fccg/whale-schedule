"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { Instance } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
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
  }, []);

  if (loading) return <div className="max-w-5xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">我的实例</h1>
          <p className="text-muted-foreground">管理和监控您的 GPU 实例</p>
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
        <div className="space-y-3">
          {instances.map((inst) => (
            <Card
              key={inst.id}
              className="bg-card border-border hover:border-[#8A5CF5]/50 transition-colors cursor-pointer"
              onClick={() => router.push(`/instances/${inst.id}`)}
            >
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-sm text-muted-foreground">{inst.id.slice(0, 8)}</span>
                    <InstanceStatusBadge status={inst.status} />
                    {inst.status === "bootstrapping" && (
                      <span className="text-xs text-muted-foreground">步骤 {inst.current_step}/6</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    创建于 {new Date(inst.created_at).toLocaleString("zh-CN")}
                    {inst.last_heartbeat_at && ` · 最近心跳: ${new Date(inst.last_heartbeat_at).toLocaleTimeString("zh-CN")}`}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-semibold ${inst.status === "ready" ? "text-green-400" : "text-muted-foreground"}`}>
                    {inst.progress_percent > 0 ? `${Math.round(inst.progress_percent)}%` : ""}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
