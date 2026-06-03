"use client";

interface MarketplaceToolbarProps {
  total: number;
  family: string;
  onFamilyChange: (value: string) => void;
  sort: string;
  onSortChange: (value: string) => void;
}

const FAMILY_TABS = ["All", "A100", "H", "6090"];
const SORTS = [
  { value: "price_asc", label: "价格最低" },
  { value: "price_desc", label: "价格最高" },
  { value: "reliability", label: "稳定性" },
];

export default function MarketplaceToolbar({
  total,
  family,
  onFamilyChange,
  sort,
  onSortChange,
}: MarketplaceToolbarProps) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/8 bg-[#141414] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Marketplace</p>
          <h1 className="text-3xl font-semibold text-white">GPU 资源市场</h1>
        </div>
        <div className="rounded-full border border-white/8 bg-black/20 px-4 py-2 text-sm text-muted-foreground">
          共 <span className="font-semibold text-white">{total}</span> 个报价
        </div>
      </div>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {FAMILY_TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => onFamilyChange(item)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                family === item
                  ? "bg-[#8A5CF5] text-white"
                  : "bg-black/20 text-muted-foreground hover:text-white"
              }`}
            >
              {item === "All" ? "全部 GPU" : item}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">排序</span>
          <div className="flex rounded-full border border-white/8 bg-black/20 p-1">
            {SORTS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => onSortChange(item.value)}
                className={`rounded-full px-3 py-1.5 transition ${
                  sort === item.value ? "bg-white text-black" : "text-muted-foreground hover:text-white"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
