"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { TestRun } from "@/lib/api";

interface TestReportPanelProps {
  testRuns: TestRun[];
  onTriggerTest: () => void;
  loading?: boolean;
}

export default function TestReportPanel({ testRuns, onTriggerTest, loading }: TestReportPanelProps) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">性能测试</CardTitle>
        <Button size="sm" variant="outline" disabled={loading} onClick={onTriggerTest}>
          运行性能测试
        </Button>
      </CardHeader>
      <CardContent>
        {testRuns.length === 0 ? (
          <p className="text-sm text-muted-foreground">尚未运行测试</p>
        ) : (
          <div className="space-y-4">
            {testRuns.map((run) => (
              <div key={run.id} className="border border-border rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">{run.type === "perf" ? "性能测试" : "连通性测试"}</span>
                  <span className={`text-xs ${run.status === "completed" ? "text-green-400" : "text-yellow-400"}`}>
                    {run.status}
                  </span>
                </div>
                {run.results && (
                  <div className="grid grid-cols-2 gap-1">
                    {run.results.map((r) => (
                      <div key={r.id} className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{r.metric_name}</span>
                        <span className={r.passed ? "text-green-400" : "text-red-400"}>
                          {r.value} {r.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
