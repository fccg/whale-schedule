"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import type { GPUOffering } from "@/lib/api";
import MarketplaceSidebar from "@/components/market/MarketplaceSidebar";
import MarketplaceToolbar from "@/components/market/MarketplaceToolbar";
import GpuOfferRow from "@/components/market/GpuOfferRow";

export default function GPUListPage() {
  const router = useRouter();
  const [gpus, setGpus] = useState<GPUOffering[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [family, setFamily] = useState("All");
  const [provider, setProvider] = useState("all");
  const [maxPrice, setMaxPrice] = useState(20);
  const [region, setRegion] = useState("all");
  const [availableOnly, setAvailableOnly] = useState(true);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("price_asc");

  const sortItems = useCallback((items: GPUOffering[], mode: string) => {
    const next = [...items];
    if (mode === "price_desc") return next.sort((a, b) => b.price_per_hour - a.price_per_hour);
    if (mode === "reliability") return next.sort((a, b) => b.reliability_score - a.reliability_score);
    return next.sort((a, b) => a.price_per_hour - b.price_per_hour);
  }, []);

  const loadGPUs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (family !== "All") params.family = family;
      if (provider !== "all") params.provider = provider;
      if (region !== "all") params.region = region;
      if (maxPrice < 20) params.max_price = String(maxPrice);
      if (search) params.search = search;
      const res = await api.getGPUs(params);
      setGpus(sortItems(res.items, sort));
      setRegions(res.filters.regions);
    } finally {
      setLoading(false);
    }
  }, [family, provider, region, maxPrice, search, sort, sortItems]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadGPUs();
  }, [loadGPUs, router]);

  const filtered = useMemo(() => {
    const items = availableOnly ? gpus.filter((item) => item.available) : gpus;
    return sortItems(items, sort);
  }, [availableOnly, gpus, sort, sortItems]);

  return (
    <div className="min-h-screen bg-[#0b0b0d]">
      <div className="mx-auto flex max-w-[1600px] gap-6 px-4 py-8">
        <MarketplaceSidebar
          search={search}
          family={family}
          maxPrice={maxPrice}
          provider={provider}
          availableOnly={availableOnly}
          regions={regions}
          selectedRegion={region}
          onSearchChange={setSearch}
          onFamilyChange={setFamily}
          onProviderChange={setProvider}
          onMaxPriceChange={setMaxPrice}
          onRegionChange={setRegion}
          onAvailableOnlyChange={setAvailableOnly}
        />

        <div className="min-w-0 flex-1 space-y-4">
          <MarketplaceToolbar total={filtered.length} family={family} onFamilyChange={setFamily} sort={sort} onSortChange={setSort} />

          {loading ? (
            <div className="rounded-2xl border border-white/8 bg-[#141414] p-8 text-muted-foreground">加载中...</div>
          ) : filtered.length === 0 ? (
            <div className="rounded-2xl border border-white/8 bg-[#141414] p-8 text-muted-foreground">
              没有匹配的 GPU 资源，请调整筛选条件。
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map((gpu) => (
                <GpuOfferRow key={gpu.id} gpu={gpu} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
