"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ConnectivityTest } from "@/lib/api";

interface ConnectivityChecklistProps {
  tests: ConnectivityTest[];
}

export default function ConnectivityChecklist({ tests }: ConnectivityChecklistProps) {
  if (!tests || tests.length === 0) {
    return (
      <Card className="bg-card border-border">
        <CardHeader><CardTitle className="text-lg">外网可达性</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-muted-foreground">尚未运行连通性测试</p></CardContent>
      </Card>
    );
  }
  return (
    <Card className="bg-card border-border">
      <CardHeader><CardTitle className="text-lg">外网可达性</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {tests.map((t) => (
          <div key={t.id} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t.target}</span>
            <div className="flex items-center gap-3">
              <span className={t.status_code === 200 ? "text-green-400" : "text-red-400"}>{t.status_code}</span>
              <span className="text-muted-foreground">{t.latency_ms.toFixed(1)} ms</span>
              <span className={t.is_direct ? "text-green-400" : "text-orange-400"}>
                {t.is_direct ? "直连" : "代理"}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
