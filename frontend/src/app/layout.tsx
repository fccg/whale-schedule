"use client";

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, clearToken } from "@/lib/api";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="zh"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Nav />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}

function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getToken());
  }, [pathname]);

  if (pathname === "/login") return null;

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-lg text-[#8A5CF5]">
            GPUSchedule
          </Link>
          <Link
            href="/"
            className={`text-sm transition-colors ${pathname === "/" || pathname.startsWith("/gpus") ? "text-white" : "text-muted-foreground hover:text-white"}`}
          >
            GPU 市场
          </Link>
          <Link
            href="/instances"
            className={`text-sm transition-colors ${pathname.startsWith("/instances") ? "text-white" : "text-muted-foreground hover:text-white"}`}
          >
            我的实例
          </Link>
        </div>
        <div className="flex items-center gap-4">
          {loggedIn ? (
            <button onClick={handleLogout} className="text-sm text-muted-foreground hover:text-white transition-colors">
              退出登录
            </button>
          ) : (
            <Link href="/login" className="text-sm text-muted-foreground hover:text-white transition-colors">
              登录
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
