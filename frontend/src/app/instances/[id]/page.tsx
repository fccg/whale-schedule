"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { InstanceDashboard } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import InstanceHeroBar from "@/components/instance/InstanceHeroBar";
import TelemetryStatTile from "@/components/instance/TelemetryStatTile";
import GpuTelemetryPanel from "@/components/instance/GpuTelemetryPanel";
import TestReportPanel from "@/components/TestReportPanel";
import ConnectivityChecklist from "@/components/ConnectivityChecklist";

const TABS = ["Telemetry", "Connect", "Tests", "Logs"] as const;

const TelemetryGauge = dynamic(() => import("@/components/instance/TelemetryGauge"), {
  ssr: false,
  loading: () => <div className="min-h-[260px] rounded-2xl border border-white/8 bg-[#141414] p-5" />,
});

const TelemetryChart = dynamic(() => import("@/components/TelemetryChart"), {
  ssr: false,
  loading: () => <div className="w-full rounded-xl bg-black/10" style={{ height: 320 }} />,
});

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatTime(value: string | null | undefined) {
  if (!value) return "无";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function cleanText(value: string | null | undefined, fallback = "—") {
  if (!value) return fallback;
  const trimmed = value.trim();
  const unwrapped = trimmed.replace(/^`+|`+$/g, "");
  return unwrapped || fallback;
}

export default function InstanceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const instanceId = params.id as string;
  const [dashboard, setDashboard] = useState<InstanceDashboard | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [connectivityLoading, setConnectivityLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Telemetry");

  const load = useCallback(async () => {
    try {
      const res = await api.getInstanceDashboard(instanceId);
      setDashboard(res);
    } finally {
      setLoading(false);
    }
  }, [instanceId]);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [instanceId, load, router]);

  const handleDestroy = async () => {
    if (!confirm("确认销毁此实例？")) return;
    await api.deleteInstance(instanceId);
    router.push("/instances");
  };

  const handleRunPerfTest = async () => {
    setTestLoading(true);
    await api.triggerTest(instanceId, "perf");
    setTestLoading(false);
    load();
  };

  const handleRunConnectivityTest = async () => {
    setConnectivityLoading(true);
    await api.triggerConnectivityTest(instanceId);
    setConnectivityLoading(false);
    load();
  };

  if (loading) return <div className="max-w-6xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;
  if (!dashboard) return <div className="max-w-6xl mx-auto px-4 py-8"><p className="text-muted-foreground">实例不存在</p></div>;

  const { instance, offering, runtime, latest_metric, metric_history, connect, tests_summary, connectivity_summary } = dashboard;
  const diskUsed = runtime?.disk_used_gb ?? 0;
  const diskTotal = runtime?.disk_total_gb ?? 0;
  const diskText = `${diskUsed.toFixed(0)} GB / ${diskTotal.toFixed(0)} GB`;
  const volumeText = runtime?.volume_total_gb != null
    ? `${runtime.volume_used_gb ?? 0} / ${runtime.volume_total_gb} GB`
    : "No Volume";

  return (
    <div className="min-h-screen bg-[#0b0b0d]">
      <div className="mx-auto max-w-[1500px] px-4 py-8">
        <button onClick={() => router.back()} className="mb-4 text-sm text-muted-foreground hover:text-white">
          &larr; 返回实例列表
        </button>

        <InstanceHeroBar instance={instance} offering={offering} runtime={runtime} onDestroy={handleDestroy} />

        <div className="mt-6 flex flex-wrap gap-2 border-b border-white/8 pb-3">
          {TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                tab === item ? "bg-[#8A5CF5] text-white" : "bg-white/6 text-muted-foreground hover:text-white"
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        {tab === "Telemetry" && (
          <div className="mt-6 grid gap-4">
            <div className="grid gap-4 xl:grid-cols-2">
              <TelemetryStatTile label="Disk Usage" value={diskText} hint="本地缓存盘" />
              <TelemetryStatTile label="Volume Usage" value={volumeText} hint="外部卷" />
            </div>
            <div className="grid gap-4 xl:grid-cols-4">
              <TelemetryStatTile label="Uptime" value={`${Math.floor((runtime.uptime_seconds ?? 0) / 3600)}h ${Math.floor(((runtime.uptime_seconds ?? 0) % 3600) / 60)}m`} />
              <TelemetryStatTile label="Processes" value={String(runtime.process_count ?? "--")} hint="当前容器内活动进程" />
              <TelemetryGauge
                label="CPU Load"
                value={latest_metric?.cpu_percent}
                sublabel={`${latest_metric?.cpu_percent?.toFixed(0) ?? "--"}%`}
              />
              <TelemetryGauge
                label="Memory"
                value={latest_metric?.memory_percent}
                color="#7B8CFF"
                sublabel={`${latest_metric?.memory_used_gb?.toFixed(1) ?? "--"} / ${latest_metric?.memory_total_gb?.toFixed(1) ?? "--"} GiB`}
              />
            </div>

            <GpuTelemetryPanel runtime={runtime} />

            <Card className="border-white/8 bg-[#141414]">
              <CardHeader>
                <CardTitle>Telemetry History</CardTitle>
              </CardHeader>
              <CardContent>
                <TelemetryChart data={metric_history} height={320} />
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "Connect" && (
          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <Card className="border-white/8 bg-[#141414]">
              <CardHeader><CardTitle>Connection</CardTitle></CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Jupyter URL</p>
                  <p className="break-all text-white">{cleanText(connect.jupyter_url)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">SSH</p>
                  <p className="text-white">{cleanText(connect.ssh_host)}:{connect.ssh_port ?? "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Provider Instance ID</p>
                  <p className="text-white font-mono text-xs">{instance.provider_instance_id || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Region</p>
                  <p className="text-white">{instance.region || offering?.region || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Hourly Price</p>
                  <p className="text-white">{instance.hourly_price != null ? `¥${instance.hourly_price}/h` : offering?.price_per_hour != null ? `¥${offering.price_per_hour}/h` : "—"}</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/8 bg-[#141414]">
              <CardHeader><CardTitle>Runtime Meta</CardTitle></CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Docker Image</p>
                  <p className="text-white">{connect.docker_image}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Image Runtype</p>
                  <p className="text-white">{connect.image_runtype}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Command Preview</p>
                  <p className="text-white">{connect.command_preview}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Environment</p>
                  <pre className="overflow-x-auto rounded-xl bg-black/20 p-3 text-xs text-white">
                    {JSON.stringify(connect.env, null, 2)}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "Tests" && (
          <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <TestReportPanel
              instanceId={instanceId}
              testRuns={tests_summary}
              onTriggerTest={handleRunPerfTest}
              loading={testLoading}
            />
            <ConnectivityChecklist
              tests={connectivity_summary}
              onRunTest={handleRunConnectivityTest}
              loading={connectivityLoading}
            />
          </div>
        )}

        {tab === "Logs" && (
          <Card className="mt-6 border-white/8 bg-[#141414]">
            <CardHeader><CardTitle>Lifecycle / Agent Logs</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
                <p className="text-white">状态: {instance.status}</p>
                <p className="mt-2">当前进度: {Math.round(instance.progress_percent)}%</p>
                <p className="mt-2">最后错误: {instance.last_error || "无"}</p>
              </div>
              <div className="rounded-2xl border border-white/6 bg-black/20 p-4">
                <p>Agent heartbeat: {formatTime(instance.last_heartbeat_at)}</p>
                <p className="mt-2">Provider instance id: {instance.provider_instance_id}</p>
                <p className="mt-2">创建时间: {formatDateTime(instance.created_at)}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
