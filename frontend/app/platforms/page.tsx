"use client";

import { useEffect, useState } from "react";
import { getPlatforms } from "@/lib/api";
import PlatformBadge from "@/components/PlatformBadge";

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
      <div className="space-y-4">
        <div className="h-8 w-48 rounded shimmer" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="glass-card p-6 space-y-3">
              <div className="h-4 w-24 rounded shimmer" />
              <div className="h-10 w-20 rounded shimmer" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-display font-extrabold text-white mb-2">
          Platforms
        </h1>
        <p className="text-slate-400 text-sm">
          AgentScore reads agents from 10 external platforms. No registration
          needed.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map((p) => (
          <div key={p.name} className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <PlatformBadge platform={p.name} />
                <h3 className="font-display font-semibold text-white">
                  {p.display_name}
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">
                {p.chain}
              </span>
            </div>
            <div className="flex gap-8">
              <div>
                <p className="text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  TOTAL
                </p>
                <p className="text-2xl font-display font-extrabold text-white">
                  {p.total_agents?.toLocaleString() || "\u2014"}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  INDEXED
                </p>
                <p className="text-2xl font-display font-extrabold text-accent">
                  {p.indexed_agents?.toLocaleString() || "0"}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
