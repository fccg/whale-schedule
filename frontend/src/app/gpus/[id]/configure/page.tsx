"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { GPUOffering } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import TemplateCard from "@/components/TemplateCard";

const TEMPLATES = ["nvidia/pytorch:26.03-py3", "nvidia/cuda:13.0-devel-ubuntu24.04", "ubuntu:24.04"];

export default function ConfigurePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [gpu, setGpu] = useState<GPUOffering | null>(null);
  const [template, setTemplate] = useState("nvidia/pytorch:26.03-py3");
  const [diskGb, setDiskGb] = useState(200);
  const [durationH, setDurationH] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [estimate, setEstimate] = useState<{ price_per_hour: number; estimated_total: number; remaining_budget: number } | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.getGPUDetail(id).then(setGpu).catch(() => router.push("/"));
  }, [id]);

  useEffect(() => {
    api.estimateCost(id, durationH).then(setEstimate).catch(() => {});
  }, [id, durationH]);

  const handleCreate = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.createInstance({
        gpu_offering_id: id,
        template,
        disk_gb: diskGb,
        duration_h: durationH,
      });
      router.push(`/instances/${res.instance.id}`);
    } catch (err: any) {
      setError(err.message || "创建失败");
    } finally {
      setLoading(false);
    }
  };

  if (!gpu) return <div className="max-w-3xl mx-auto px-4 py-8"><p className="text-muted-foreground">加载中...</p></div>;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <button onClick={() => router.back()} className="text-sm text-muted-foreground hover:text-white mb-4 block">
        &larr; 返回
      </button>

      <h1 className="text-2xl font-bold mb-6">配置实例 — {gpu.gpu_model}</h1>

      <div className="space-y-6">
        <Card className="bg-card border-border">
          <CardHeader><CardTitle className="text-lg">GPU 配置概览</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-muted-foreground">型号: <span className="text-white">{gpu.gpu_model}</span></div>
            <div className="text-muted-foreground">区域: <span className="text-white">{gpu.region}</span></div>
            <div className="text-muted-foreground">显存: <span className="text-white">{gpu.vram_gb} GB</span></div>
            <div className="text-muted-foreground">内存: <span className="text-white">{gpu.memory_gb} GB</span></div>
            <div className="text-muted-foreground">价格: <span className="text-[#8A5CF5] font-semibold">¥{gpu.price_per_hour}/h</span></div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader><CardTitle className="text-lg">选择模板</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {TEMPLATES.map((t) => (
              <TemplateCard key={t} value={t} label={t} selected={template === t} onSelect={setTemplate} />
            ))}
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader><CardTitle className="text-lg">磁盘容量</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Slider value={[diskGb]} onValueChange={(v) => setDiskGb(Array.isArray(v) ? v[0] : v)}
                min={50} max={1000} step={50} className="flex-1" />
              <span className="text-sm font-mono w-16 text-right">{diskGb} GB</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader><CardTitle className="text-lg">使用时长</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Slider value={[durationH]} onValueChange={(v) => setDurationH(Array.isArray(v) ? v[0] : v)}
                min={1} max={24} step={1} className="flex-1" />
              <span className="text-sm font-mono w-20 text-right">{durationH} 小时</span>
            </div>
          </CardContent>
        </Card>

        {estimate && (
          <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
            <span className="text-muted-foreground">预估费用</span>
            <span className="text-2xl font-bold text-[#8A5CF5]">¥{estimate.estimated_total.toFixed(2)}</span>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button
          className="w-full bg-[#8A5CF5] hover:bg-[#7B4FE0] h-12 text-lg"
          disabled={loading}
          onClick={handleCreate}
        >
          {loading ? "创建中..." : "一键开机"}
        </Button>
      </div>
    </div>
  );
}
