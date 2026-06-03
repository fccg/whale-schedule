"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { Instance, Metric, TestRun, ConnectivityTest } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import InstanceStatusBadge from "@/components/InstanceStatusBadge";
import CircularStatCard from "@/components/CircularStatCard";
import TelemetryChart from "@/components/TelemetryChart";
import TestReportPanel from "@/components/TestReportPanel";
import ConnectivityChecklist from "@/components/ConnectivityChecklist";

const STEP_LABELS = ["", "apt + CUDA Toolkit", "CUDA 13 + cuDNN", "NGC PyTorch 容器", "Codex + Claude CLI", "S3 挂载 + 数据集", "gpu-agent 部署"];

export default function InstanceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const instanceId = params.id as string;
  const [instance, setInstance] = useState<Instance | null>(null);
  const [metrics, setMetrics] = useState<Metric | null>(null);
  const [history, setHistory] = useState<Metric[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [connectivity, setConnectivity] = useState<ConnectivityTest[]>([]);
  const [testLoading, setTestLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await api.getInstance(instanceId);
      setInstance(res.instance);
      setMetrics(res.metrics);
      if (res.instance.status === "ready") {
        const [testsRes, connRes, metricsRes] = await Promise.all([
          api.getTests(instanceId).catch(() => ({ test_runs: [] })),
          api.getConnectivity(instanceId).catch(() => ({ connectivity_tests: [] })),
          api.getInstanceMetrics(instanceId).catch(() => ({ latest: null, history: [] })),
        ]);
        setTestRuns(testsRes.test_runs);
        setConnectivity(connRes.connectivity_tests);
        setHistory(metricsRes.history);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [instanceId]);

  const handleDestroy = async () => {
    if (!confirm("确认销毁此实例？")) return;
    await api.deleteInstance(instanceId);
    router.push("/instances");
  };

  if (loading) return <div className="max-w-5xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;
  if (!instance) return <div className="max-w-5xl mx-auto px-4 py-8"><p className="text-muted-foreground">实例不存在</p></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-white mb-4 block">
        &larr; 返回实例列表
      </button>

      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold">实例 {instance.id.slice(0, 12)}</h1>
            <InstanceStatusBadge status={instance.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            Provider: {instance.provider} · GPU Offering: {instance.gpu_offering_id}
            {instance.last_heartbeat_at && ` · 最近心跳: ${new Date(instance.last_heartbeat_at).toLocaleTimeString("zh-CN")}`}
          </p>
        </div>
        {instance.status !== "destroyed" && (
          <Button variant="destructive" size="sm" onClick={handleDestroy}>
            销毁实例
          </Button>
        )}
      </div>

      {instance.status !== "ready" && instance.status !== "destroyed" && instance.status !== "failed" && (
        <Card className="bg-card border-border mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2 text-sm">
              <span className="text-muted-foreground">
                {instance.status === "provisioning" ? "正在分配 GPU 实例..." :
                 instance.status === "testing" ? "正在运行健康检查..." :
                 `正在安装环境... ${STEP_LABELS[instance.current_step] || ""}`}
              </span>
              <span className="text-[#8A5CF5]">{Math.round(instance.progress_percent)}%</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-[#8A5CF5] transition-all duration-1000 rounded-full"
                style={{ width: `${instance.progress_percent}%` }} />
            </div>
          </CardContent>
        </Card>
      )}

      {instance.status === "failed" && (
        <Card className="bg-red-500/10 border-red-500/30 mb-6">
          <CardContent className="p-4">
            <p className="text-sm text-red-400 font-semibold">启动失败</p>
            {instance.last_error && <p className="text-sm text-red-300 mt-1">{instance.last_error}</p>}
          </CardContent>
        </Card>
      )}

      {instance.status === "degraded" && (
        <Card className="bg-orange-500/10 border-orange-500/30 mb-6">
          <CardContent className="p-4">
            <p className="text-sm text-orange-400">
              监控失联 — 最近心跳: {instance.last_heartbeat_at ? new Date(instance.last_heartbeat_at).toLocaleTimeString("zh-CN") : "无"}
            </p>
          </CardContent>
        </Card>
      )}

      {metrics && (
        <Card className="bg-card border-border mb-6">
          <CardHeader><CardTitle className="text-lg">资源监控</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-8 justify-center">
              <CircularStatCard label="CPU" value={metrics.cpu_percent} color="#8A5CF5" />
              <CircularStatCard label="内存" value={metrics.memory_percent} color="#60A5FA" />
              <CircularStatCard label="GPU" value={metrics.gpu_util_percent} color="#34D399" />
              <CircularStatCard label="显存" value={metrics.gpu_vram_percent} color="#F472B6" />
            </div>
            <div className="grid grid-cols-4 gap-4 mt-6 text-center text-sm">
              <div>
                <span className="text-muted-foreground">内存已用</span>
                <p className="text-white font-semibold">{metrics.memory_used_gb?.toFixed(1)} / {metrics.memory_total_gb?.toFixed(0)} GB</p>
              </div>
              <div>
                <span className="text-muted-foreground">磁盘已用</span>
                <p className="text-white font-semibold">{metrics.disk_used_gb?.toFixed(1)} / {metrics.disk_total_gb?.toFixed(0)} GB</p>
              </div>
              <div>
                <span className="text-muted-foreground">上传</span>
                <p className="text-white font-semibold">{metrics.net_up_mbps?.toFixed(1)} Mbps</p>
              </div>
              <div>
                <span className="text-muted-foreground">下载</span>
                <p className="text-white font-semibold">{metrics.net_down_mbps?.toFixed(1)} Mbps</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {history.length > 0 && (
        <Card className="bg-card border-border mb-6">
          <CardHeader><CardTitle className="text-lg">监控历史</CardTitle></CardHeader>
          <CardContent>
            <TelemetryChart data={history} />
          </CardContent>
        </Card>
      )}

      {instance.status === "ready" && (
        <>
          <div className="mb-6">
            <TestReportPanel
              testRuns={testRuns}
              onTriggerTest={async (type) => {
                setTestLoading(true);
                await api.triggerTest(instanceId, type);
                setTestLoading(false);
                load();
              }}
              loading={testLoading}
            />
          </div>
          <div className="mb-6">
            <ConnectivityChecklist tests={connectivity} />
          </div>
        </>
      )}

      <Card className="bg-card border-border">
        <CardHeader><CardTitle className="text-lg">实例信息</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">实例 ID: <span className="text-white font-mono">{instance.id}</span></div>
          <div className="text-muted-foreground">状态: <InstanceStatusBadge status={instance.status} /></div>
          <div className="text-muted-foreground">Provider: <span className="text-white">{instance.provider}</span></div>
          <div className="text-muted-foreground">创建时间: <span className="text-white">{new Date(instance.created_at).toLocaleString("zh-CN")}</span></div>
        </CardContent>
      </Card>
    </div>
  );
}
