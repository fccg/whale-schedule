"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { GPUOffering } from "@/lib/api";
import GPURentalCard from "@/components/GPURentalCard";
import SearchAndFilter from "@/components/SearchAndFilter";

const FAMILIES = ["All", "A100", "H", "6090"];

export default function GPUListPage() {
  const router = useRouter();
  const [gpus, setGpus] = useState<GPUOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [family, setFamily] = useState("All");
  const [maxPrice, setMaxPrice] = useState(20);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    loadGPUs();
  }, [family, maxPrice]);

  async function loadGPUs() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (family !== "All") params.family = family;
      if (maxPrice < 20) params.max_price = String(maxPrice);
      const res = await api.getGPUs(params);
      setGpus(res.gpus);
    } finally {
      setLoading(false);
    }
  }

  const filtered = gpus.filter(
    (g) =>
      g.gpu_model.toLowerCase().includes(search.toLowerCase()) ||
      g.region.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">GPU 市场</h1>
        <p className="text-muted-foreground">跨供应商统一调度 GPU 资源</p>
      </div>

      <SearchAndFilter
        search={search}
        onSearchChange={setSearch}
        family={family}
        onFamilyChange={setFamily}
        families={FAMILIES}
        maxPrice={maxPrice}
        onMaxPriceChange={setMaxPrice}
      />

      {loading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground">没有匹配的 GPU 资源</p>
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
          {filtered.map((gpu) => (
            <GPURentalCard key={gpu.id} gpu={gpu} />
          ))}
        </div>
      )}
    </div>
  );
}
