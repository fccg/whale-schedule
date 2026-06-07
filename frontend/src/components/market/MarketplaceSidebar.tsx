"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface MarketplaceSidebarProps {
  search: string;
  families: string[];
  family: string;
  models: string[];
  selectedModel: string;
  maxPrice: number;
  providers: string[];
  provider: string;
  availableOnly: boolean;
  regions: string[];
  selectedRegion: string;
  onSearchChange: (value: string) => void;
  onFamilyChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onProviderChange: (value: string) => void;
  onMaxPriceChange: (value: number) => void;
  onRegionChange: (value: string) => void;
  onAvailableOnlyChange: (value: boolean) => void;
}

function familyLabel(value: string) {
  if (value === "A") return "A 系列";
  if (value === "H") return "H 系列";
  if (value === "RTX") return "RTX 系列";
  if (value === "OTHER") return "其他";
  return value;
}

export default function MarketplaceSidebar(props: MarketplaceSidebarProps) {
  const {
    search,
    families,
    family,
    models,
    selectedModel,
    maxPrice,
    providers,
    provider,
    availableOnly,
    regions,
    selectedRegion,
    onSearchChange,
    onFamilyChange,
    onModelChange,
    onProviderChange,
    onMaxPriceChange,
    onRegionChange,
    onAvailableOnlyChange,
  } = props;

  return (
    <aside className="w-full max-w-xs shrink-0">
      <Card className="sticky top-20 border-white/8 bg-[#141414]">
        <CardHeader className="border-b border-white/6">
          <CardTitle className="text-lg">Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-4">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">关键词</p>
            <Input
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="搜索型号、区域、Provider"
              className="border-white/10 bg-black/20"
            />
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">GPU Family</p>
            <div className="grid grid-cols-2 gap-2">
              {["All", ...families].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onFamilyChange(item)}
                  className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                    family === item
                      ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                      : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                  }`}
                >
                  {item === "All" ? "全部" : familyLabel(item)}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">GPU Model</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => onModelChange("all")}
                className={`rounded-full border px-3 py-1.5 text-xs transition ${
                  selectedModel === "all"
                    ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                    : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                }`}
              >
                全部
              </button>
              {models.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onModelChange(item)}
                  className={`rounded-full border px-3 py-1.5 text-xs transition ${
                    selectedModel === item
                      ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                      : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Provider</p>
            <div className="flex flex-wrap gap-2">
              {["all", ...providers].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onProviderChange(item)}
                  className={`rounded-full border px-3 py-1.5 text-xs transition ${
                    provider === item
                      ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                      : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                  }`}
                >
                  {item === "all" ? "全部" : item}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <span>Price Ceiling</span>
              <span className="text-white">¥{maxPrice.toFixed(1)}/h</span>
            </div>
            <Slider
              value={[maxPrice]}
              onValueChange={(values) => onMaxPriceChange(Array.isArray(values) ? (values[0] ?? maxPrice) : values)}
              min={2}
              max={20}
              step={0.5}
            />
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Region</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => onRegionChange("all")}
                className={`rounded-full border px-3 py-1.5 text-xs transition ${
                  selectedRegion === "all"
                    ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                    : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                }`}
              >
                全部
              </button>
              {regions.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onRegionChange(item)}
                  className={`rounded-full border px-3 py-1.5 text-xs transition ${
                    selectedRegion === item
                      ? "border-[#8A5CF5] bg-[#8A5CF5]/15 text-white"
                      : "border-white/8 bg-black/15 text-muted-foreground hover:text-white"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 rounded-lg border border-white/8 bg-black/15 px-3 py-3">
            <Checkbox checked={availableOnly} onCheckedChange={(checked) => onAvailableOnlyChange(Boolean(checked))} />
            <div>
              <p className="text-sm text-white">仅显示可立即开机</p>
              <p className="text-xs text-muted-foreground">过滤掉不可用或缺货的报价</p>
            </div>
          </label>
        </CardContent>
      </Card>
    </aside>
  );
}
