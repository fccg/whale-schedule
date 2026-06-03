"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { LaunchPayload } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import TemplateSelector from "@/components/launch/TemplateSelector";
import LaunchSummaryCard from "@/components/launch/LaunchSummaryCard";

export default function ConfigurePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [payload, setPayload] = useState<LaunchPayload | null>(null);
  const [templateId, setTemplateId] = useState("pytorch");
  const [diskGb, setDiskGb] = useState(200);
  const [durationH, setDurationH] = useState(6);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.getLaunchPayload(id).then((res) => {
      setPayload(res);
      setTemplateId(res.defaults.template_id);
      setDiskGb(res.defaults.disk_gb);
      setDurationH(res.defaults.duration_h);
    }).catch(() => router.push("/"));
  }, [id, router]);

  const selectedTemplate = payload?.templates.find((item) => item.id === templateId);
  const estimatedTotal = (payload?.offering.price_per_hour ?? 0) * durationH;
  const remainingBudget = payload?.budget.remaining_budget ?? 0;

  const handleCreate = async () => {
    if (!payload || !selectedTemplate) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.createInstance({
        gpu_offering_id: id,
        template: selectedTemplate.image,
        disk_gb: diskGb,
        duration_h: durationH,
      });
      router.push(`/instances/${res.instance.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  };

  if (!payload) return <div className="max-w-6xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;

  const { offering, templates } = payload;

  return (
    <div className="min-h-screen bg-[#0b0b0d]">
      <div className="mx-auto flex max-w-[1400px] gap-6 px-4 py-8">
        <div className="min-w-0 flex-1 space-y-6">
          <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-white">
            &larr; 返回市场
          </button>

          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Launch</p>
            <h1 className="text-3xl font-semibold text-white">一键开机 · {offering.gpu_model}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {offering.host_display_name} · {offering.region} · {offering.provider}
            </p>
          </div>

          <Card className="border-white/8 bg-[#141414]">
            <CardHeader>
              <CardTitle>镜像模板</CardTitle>
            </CardHeader>
            <CardContent>
              <TemplateSelector templates={templates} selectedId={templateId} onSelect={setTemplateId} />
            </CardContent>
          </Card>

          <Card className="border-white/8 bg-[#141414]">
            <CardHeader>
              <CardTitle>实例规格</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-6 lg:grid-cols-2">
              <div className="space-y-3 rounded-2xl border border-white/6 bg-black/20 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">磁盘容量</span>
                  <span className="text-xl font-semibold text-white">{diskGb} GB</span>
                </div>
                <Slider value={[diskGb]} onValueChange={(v) => setDiskGb(Array.isArray(v) ? (v[0] ?? diskGb) : v)} min={100} max={1500} step={50} />
                <p className="text-sm text-muted-foreground">本地 NVMe 用于模型、数据集和日志缓存。</p>
              </div>

              <div className="space-y-3 rounded-2xl border border-white/6 bg-black/20 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">最长运行时长</span>
                  <span className="text-xl font-semibold text-white">{durationH} 小时</span>
                </div>
                <Slider value={[durationH]} onValueChange={(v) => setDurationH(Array.isArray(v) ? (v[0] ?? durationH) : v)} min={1} max={24} step={1} />
                <p className="text-sm text-muted-foreground">用于预算控制和回收策略，创建前会进行额度校验。</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/8 bg-[#141414]">
            <CardHeader>
              <CardTitle>环境准备内容</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {[
                "CUDA / cuDNN",
                "PyTorch 容器",
                "gpu-agent 心跳",
                "性能测试报告",
                "连通性检查",
                "预算阻断",
              ].map((item) => (
                <div key={item} className="rounded-2xl border border-white/6 bg-black/20 px-4 py-3 text-sm text-white">
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>

          {error && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/8 p-4 text-sm text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="w-full max-w-md shrink-0">
          <LaunchSummaryCard
            offering={offering}
            estimatedTotal={estimatedTotal}
            remainingBudget={remainingBudget}
            durationH={durationH}
            diskGb={diskGb}
            loading={loading}
            onLaunch={handleCreate}
          />
        </div>
      </div>
    </div>
  );
}
