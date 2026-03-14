"use client";

import { useEffect, useState } from "react";
import { getPlatforms } from "@/lib/api";
import PlatformBadge from "@/components/PlatformBadge";

const PLATFORM_COLORS: Record<string, string> = {
  virtuals: "from-purple-500/10 to-purple-500/5 border-purple-200",
  olas: "from-blue-500/10 to-blue-500/5 border-blue-200",
  fetch: "from-yellow-500/10 to-yellow-500/5 border-yellow-200",
  elizaos: "from-green-500/10 to-green-500/5 border-green-200",
  "erc-8004": "from-orange-500/10 to-orange-500/5 border-orange-200",
  talus: "from-pink-500/10 to-pink-500/5 border-pink-200",
  wayfinder: "from-cyan-500/10 to-cyan-500/5 border-cyan-200",
  freysa: "from-red-500/10 to-red-500/5 border-red-200",
};

export default function PlatformsPage() {
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPlatforms()
      .then((data) => setPlatforms(data.platforms || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-9 w-40 rounded-xl shimmer" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="glass-card p-6 space-y-4">
              <div className="h-5 w-28 rounded shimmer" />
              <div className="h-10 w-24 rounded shimmer" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-black text-gray-900 mb-2">
          Platforms
        </h1>
        <p className="text-gray-400 text-sm font-body">
          AgentScore reads agents from {platforms.length} external platforms — no registration required.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map((p) => {
          const colorClass = PLATFORM_COLORS[p.name?.toLowerCase()] || "from-gray-100 to-gray-50 border-gray-200";
          const coverage = p.total_agents > 0
            ? Math.round((p.indexed_agents / p.total_agents) * 100)
            : 0;

          return (
            <div
              key={p.name}
              className={`rounded-2xl p-6 border bg-gradient-to-br ${colorClass} transition-all hover:shadow-md hover:-translate-y-1 space-y-4`}
            >
              {/* Platform header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <PlatformBadge platform={p.name} />
                  <h3 className="font-display font-bold text-gray-900 text-base">
                    {p.display_name}
                  </h3>
                </div>
                <span className="text-[11px] text-gray-400 font-mono bg-white/60 px-2 py-1 rounded-md border border-white/80">
                  {p.chain}
                </span>
              </div>

              {/* Stats */}
              <div className="flex items-end gap-8">
                <div>
                  <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-1">
                    Total Agents
                  </p>
                  <p className="text-2xl font-display font-black text-gray-900">
                    {p.total_agents?.toLocaleString() || "—"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-1">
                    Indexed
                  </p>
                  <p className="text-2xl font-display font-black text-accent">
                    {p.indexed_agents?.toLocaleString() || "0"}
                  </p>
                </div>
                {coverage > 0 && (
                  <div className="ml-auto text-right">
                    <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-1">
                      Coverage
                    </p>
                    <p className="text-lg font-display font-bold text-blue-600">
                      {coverage}%
                    </p>
                  </div>
                )}
              </div>

              {/* Progress bar */}
              {p.total_agents > 0 && (
                <div className="w-full bg-white/50 rounded-full h-1.5">
                  <div
                    className="bg-accent h-1.5 rounded-full transition-all"
                    style={{ width: `${Math.min(coverage, 100)}%` }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
