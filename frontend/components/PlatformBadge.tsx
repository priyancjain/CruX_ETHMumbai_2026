"use client";

const PLATFORM_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  virtuals:   { label: "Virtuals",    bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  olas:       { label: "Olas",        bg: "bg-blue-500/10",   text: "text-blue-400",   border: "border-blue-500/20" },
  fetch:      { label: "Fetch.ai",    bg: "bg-cyan-500/10",   text: "text-cyan-400",   border: "border-cyan-500/20" },
  elizaos:    { label: "ElizaOS",     bg: "bg-emerald-500/10",text: "text-emerald-400",border: "border-emerald-500/20" },
  erc8004:    { label: "ERC-8004",    bg: "bg-amber-500/10",  text: "text-amber-400",  border: "border-amber-500/20" },
  talus:      { label: "Talus",       bg: "bg-pink-500/10",   text: "text-pink-400",   border: "border-pink-500/20" },
  wayfinder:  { label: "Wayfinder",   bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/20" },
  freysa:     { label: "Freysa",      bg: "bg-rose-500/10",   text: "text-rose-400",   border: "border-rose-500/20" },
  agentlayer: { label: "AgentLayer",  bg: "bg-orange-500/10", text: "text-orange-400", border: "border-orange-500/20" },
  sentient:   { label: "Sentient",    bg: "bg-teal-500/10",   text: "text-teal-400",   border: "border-teal-500/20" },
};

export default function PlatformBadge({ platform }: { platform: string }) {
  const config = PLATFORM_CONFIG[platform] || {
    label: platform,
    bg: "bg-slate-500/10",
    text: "text-slate-400",
    border: "border-slate-500/20",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-mono font-medium tracking-wide border ${config.bg} ${config.text} ${config.border}`}
    >
      {config.label}
    </span>
  );
}
