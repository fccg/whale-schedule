"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";

interface SearchAndFilterProps {
  search: string;
  onSearchChange: (v: string) => void;
  family: string;
  onFamilyChange: (v: string) => void;
  families: string[];
  maxPrice: number;
  onMaxPriceChange: (v: number) => void;
  priceMin?: number;
  priceMax?: number;
}

export default function SearchAndFilter({
  search, onSearchChange, family, onFamilyChange, families,
  maxPrice, onMaxPriceChange, priceMin = 1, priceMax = 20,
}: SearchAndFilterProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6 items-center">
      <Input placeholder="搜索型号或区域..." value={search}
        onChange={(e) => onSearchChange(e.target.value)} className="w-64" />
      <Select value={family} onValueChange={(v) => onFamilyChange(v || "All")}>
        <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
        <SelectContent>
          {families.map((f) => (
            <SelectItem key={f} value={f}>{f === "All" ? "全部型号" : f}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>最高 ¥{maxPrice}/h</span>
        <Slider value={[maxPrice]} onValueChange={(v) => onMaxPriceChange(Array.isArray(v) ? (v[0] ?? maxPrice) : v)}
          min={priceMin} max={priceMax} step={1} className="w-32" />
      </div>
    </div>
  );
}
