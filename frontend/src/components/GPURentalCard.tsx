"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GPUOffering } from "@/lib/api";

const FAMILY_COLORS: Record<string, string> = {
  A: "text-blue-400",
  H: "text-green-400",
  RTX: "text-orange-400",
};

interface GPURentalCardProps {
  gpu: GPUOffering;
}

export default function GPURentalCard({ gpu }: GPURentalCardProps) {
  const router = useRouter();
  const familyColor = FAMILY_COLORS[gpu.gpu_family] || "text-gray-400";
  return (
    <Card
      className="bg-card border-border hover:border-[#8A5CF5]/50 transition-colors cursor-pointer"
      onClick={() => router.push(`/gpus/${gpu.id}/configure`)}
    >
      <CardContent className="p-5 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-lg">{gpu.gpu_model}</h3>
            <p className="text-sm text-muted-foreground">{gpu.region}</p>
          </div>
          <Badge variant="outline" className={familyColor}>{gpu.gpu_family}</Badge>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">显存: <span className="text-white">{gpu.vram_gb} GB</span></div>
          <div className="text-muted-foreground">内存: <span className="text-white">{gpu.memory_gb} GB</span></div>
          <div className="text-muted-foreground">CPU: <span className="text-white">{gpu.cpu_cores} 核</span></div>
          <div className="text-muted-foreground">磁盘: <span className="text-white">{gpu.disk_gb} GB</span></div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <span className="text-2xl font-bold text-[#8A5CF5]">
            ¥{gpu.price_per_hour}<span className="text-sm text-muted-foreground font-normal">/h</span>
          </span>
          <Button size="sm" className="bg-[#8A5CF5] hover:bg-[#7B4FE0]"
            onClick={(e) => { e.stopPropagation(); router.push(`/gpus/${gpu.id}/configure`); }}>
            选配开机
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
