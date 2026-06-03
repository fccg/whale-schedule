"use client";

interface TemplateCardProps {
  value: string;
  label: string;
  selected: boolean;
  onSelect: (value: string) => void;
}

export default function TemplateCard({ value, label, selected, onSelect }: TemplateCardProps) {
  return (
    <div
      onClick={() => onSelect(value)}
      className={`p-3 rounded-lg border cursor-pointer transition-colors text-sm ${
        selected ? "border-[#8A5CF5] bg-[#8A5CF5]/10" : "border-border hover:border-muted-foreground"
      }`}
    >
      {label}
    </div>
  );
}
