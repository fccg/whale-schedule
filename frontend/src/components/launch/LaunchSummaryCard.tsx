"use client";

import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GPUOffering } from "@/lib/api";

interface LaunchSummaryCardProps {
  offering: GPUOffering;
  estimatedTotal: number;
  walletBalance: number;
  walletCurrency: string;
  providerBudgetEnabled: boolean;
  providerBudgetRemaining: number | null;
  effectiveAvailable: number;
  insufficientReason: "wallet" | "provider_budget" | null;
  durationH: number;
  diskGb: number;
  onLaunch: () => void;
  loading?: boolean;
}

export default function LaunchSummaryCard({
  offering,
  estimatedTotal,
  walletBalance,
  walletCurrency,
  providerBudgetEnabled,
  providerBudgetRemaining,
  effectiveAvailable,
  insufficientReason,
  durationH,
  diskGb,
  onLaunch,
  loading,
}: LaunchSummaryCardProps) {
  const walletInsufficient = insufficientReason === "wallet";
  const providerBudgetInsufficient = insufficientReason === "provider_budget";
  const launchDisabled = Boolean(loading || walletInsufficient || providerBudgetInsufficient);
  const currencySymbol = walletCurrency === "CNY" ? "¥" : `${walletCurrency} `;

  return (
    <Card className="sticky top-20 border-white/8 bg-[#141414]">
      <CardHeader className="border-b border-white/6">
        <CardTitle className="text-xl">资金摘要</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 pt-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-semibold text-white">{offering.gpu_model}</h2>
            {offering.verified && <ShieldCheck className="h-4 w-4 text-emerald-400" />}
          </div>
          <p className="text-sm text-muted-foreground">
            {offering.provider} · {offering.region} · {offering.host_display_name}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 rounded-2xl border border-white/6 bg-black/20 p-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">GPU</p>
            <p className="text-sm text-white">{offering.vram_gb} GB VRAM</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Compute</p>
            <p className="text-sm text-white">{offering.cpu_cores} CPU / {offering.memory_gb} GB RAM</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Disk</p>
            <p className="text-sm text-white">{diskGb} GB</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Duration</p>
            <p className="text-sm text-white">{durationH} 小时</p>
          </div>
        </div>

        <div className="space-y-3 rounded-2xl border border-white/6 bg-black/20 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">单价</span>
            <span className="text-white">¥{offering.price_per_hour.toFixed(2)}/h</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">预估总价</span>
            <span className="text-2xl font-semibold text-white">¥{estimatedTotal.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{offering.provider.toUpperCase()} 钱包余额</span>
            <span className={walletInsufficient ? "text-red-400" : "text-emerald-400"}>
              {currencySymbol}{walletBalance.toFixed(2)}
            </span>
          </div>
          {providerBudgetEnabled && providerBudgetRemaining !== null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">平台 {offering.provider.toUpperCase()} 内部额度</span>
              <span className={providerBudgetInsufficient ? "text-red-400" : "text-emerald-400"}>
                ¥{providerBudgetRemaining.toFixed(2)}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">实际可用额度</span>
            <span className={launchDisabled ? "text-red-400" : "text-emerald-400"}>¥{effectiveAvailable.toFixed(2)}</span>
          </div>
        </div>

        {walletInsufficient && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/8 p-4 text-sm text-red-300">
            AutoDL 账户余额不足，请前往 AutoDL 控制台充值后重试。
          </div>
        )}

        {providerBudgetInsufficient && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/8 p-4 text-sm text-red-300">
            平台分配给 AutoDL 的可用额度不足，请联系管理员调整预算。
          </div>
        )}

        <Button
          className="h-12 w-full bg-[#8A5CF5] text-base hover:bg-[#7A49F2]"
          disabled={launchDisabled}
          onClick={onLaunch}
        >
          {loading ? "创建中..." : "一键开机"}
        </Button>
      </CardContent>
    </Card>
  );
}
