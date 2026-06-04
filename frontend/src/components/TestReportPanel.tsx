"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { TestRun } from "@/lib/api";
import { api } from "@/lib/api";

interface TestReportPanelProps {
  instanceId: string;
  testRuns: TestRun[];
  onTriggerTest: () => void;
  loading?: boolean;
}

export default function TestReportPanel({ instanceId, testRuns, onTriggerTest, loading }: TestReportPanelProps) {
  const perfRuns = testRuns.filter((r) => r.type === "perf");

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">性能测试</CardTitle>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            disabled={perfRuns.length === 0}
            onClick={() => api.exportTests(instanceId, "json")}
          >
            JSON
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={perfRuns.length === 0}
            onClick={() => api.exportTests(instanceId, "csv")}
          >
            CSV
          </Button>
          <Button size="sm" variant="outline" disabled={loading} onClick={onTriggerTest}>
            运行性能测试
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {perfRuns.length === 0 ? (
          <p className="text-sm text-muted-foreground">尚未运行测试</p>
        ) : (
          <div className="space-y-4">
            {perfRuns.map((run) => (
              <div key={run.id} className="border border-border rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">性能测试</span>
                  <span className={`text-xs ${run.status === "completed" ? "text-green-400" : "text-yellow-400"}`}>
                    {run.status}
                  </span>
                </div>
                {run.results && run.results.length > 0 ? (
                  <div className="grid grid-cols-2 gap-1">
                    {run.results.map((r) => (
                      <div key={r.id} className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{r.metric_name}</span>
                        <span className={r.passed ? "text-green-400" : "text-muted-foreground"}>
                          {r.value != null ? `${r.value} ${r.unit}` : "pending"}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">测试结果待采集（需 GPU agent 在线）</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
