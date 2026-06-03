"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fn = isRegister ? api.register : api.login;
      const res = await fn(username, password);
      setToken(res.token);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-md mx-4 bg-card border-border">
        <CardHeader>
          <CardTitle className="text-center text-2xl">
            {isRegister ? "注册" : "登录"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                placeholder="用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
              />
            </div>
            <div>
              <Input
                type="password"
                placeholder="密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full bg-[#8A5CF5] hover:bg-[#7B4FE0]" disabled={loading}>
              {loading ? "处理中..." : isRegister ? "注册" : "登录"}
            </Button>
          </form>
          <p className="text-sm text-muted-foreground text-center mt-4">
            {isRegister ? "已有账号？" : "没有账号？"}
            <button
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(""); }}
              className="text-[#8A5CF5] hover:underline ml-1"
            >
              {isRegister ? "去登录" : "去注册"}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
