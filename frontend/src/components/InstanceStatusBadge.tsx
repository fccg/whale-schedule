"use client";

import { Badge } from "@/components/ui/badge";

export const STATUS_MAP: Record<string, { label: string; color: string }> = {
  provisioning: { label: "分配中", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  bootstrapping: { label: "环境安装中", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  testing: { label: "健康检查中", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  ready: { label: "Running", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  degraded: { label: "监控失联", color: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
  failed: { label: "启动失败", color: "bg-red-500/20 text-red-400 border-red-500/30" },
  destroyed: { label: "已销毁", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

interface InstanceStatusBadgeProps {
  status: string;
}

export default function InstanceStatusBadge({ status }: InstanceStatusBadgeProps) {
  const s = STATUS_MAP[status] || STATUS_MAP.provisioning;
  return <Badge variant="outline" className={s.color}>{s.label}</Badge>;
}
