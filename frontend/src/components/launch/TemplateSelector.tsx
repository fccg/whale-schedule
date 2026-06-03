"use client";

import type { TemplateOption } from "@/lib/api";

interface TemplateSelectorProps {
  templates: TemplateOption[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function TemplateSelector({ templates, selectedId, onSelect }: TemplateSelectorProps) {
  return (
    <div className="grid gap-3">
      {templates.map((template) => (
        <button
          key={template.id}
          type="button"
          onClick={() => onSelect(template.id)}
          className={`rounded-2xl border p-4 text-left transition ${
            template.id === selectedId
              ? "border-[#8A5CF5] bg-[#8A5CF5]/10"
              : "border-white/8 bg-[#111111] hover:border-white/20"
          }`}
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <div>
              <p className="text-base font-semibold text-white">{template.label}</p>
              <p className="text-xs text-muted-foreground">{template.image}</p>
            </div>
            {template.recommended && (
              <span className="rounded-full bg-[#8A5CF5] px-2 py-1 text-[11px] uppercase tracking-[0.2em] text-white">
                Recommended
              </span>
            )}
          </div>
          <p className="mb-3 text-sm text-muted-foreground">{template.description}</p>
          <div className="flex flex-wrap gap-2">
            {template.highlights.map((item) => (
              <span key={item} className="rounded-full bg-white/6 px-2 py-1 text-xs text-white/80">
                {item}
              </span>
            ))}
          </div>
        </button>
      ))}
    </div>
  );
}
