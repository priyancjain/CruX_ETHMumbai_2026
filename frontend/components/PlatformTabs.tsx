"use client";

const TABS = [
  { key: "all", label: "All" },
  { key: "virtuals", label: "Virtuals" },
  { key: "olas", label: "Olas" },
  { key: "fetch", label: "Fetch.ai" },
];

function formatCount(n: number): string {
  if (n >= 10000) {
    return `${Math.floor(n / 1000)}K+`;
  }
  return n.toLocaleString();
}

interface PlatformTabsProps {
  active: string;
  onSelect: (platform: string) => void;
  counts?: Record<string, number>;
}

export default function PlatformTabs({ active, onSelect, counts }: PlatformTabsProps) {
  return (
    <div className="flex gap-1.5 p-1 bg-surface-1/80 rounded-xl border border-surface-3/50 w-fit">
      {TABS.map((tab) => {
        const count = counts?.[tab.key];
        return (
          <button
            key={tab.key}
            onClick={() => onSelect(tab.key)}
            className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
              ${
                active === tab.key
                  ? "bg-accent/15 text-accent shadow-glow border border-accent/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-2/50 border border-transparent"
              }`}
          >
            <span className="font-display">{tab.label}</span>
            {count != null && count > 0 && (
              <span className={`ml-1.5 text-[10px] font-mono ${
                active === tab.key ? "text-accent/60" : "text-slate-600"
              }`}>
                {formatCount(count)}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
