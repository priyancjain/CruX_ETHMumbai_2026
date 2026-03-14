"use client";

import { useEffect, useState } from "react";
import { getLeaderboard } from "@/lib/api";
import PlatformBadge from "@/components/PlatformBadge";

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [tierFilter, setTierFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLeaderboard();
  }, [tierFilter]);

  async function loadLeaderboard() {
    setLoading(true);
    try {
      const data = await getLeaderboard(tierFilter || undefined);
      setEntries(data.leaderboard || []);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-display font-extrabold text-white">
          Leaderboard
        </h1>
        <div className="flex gap-1 p-1 bg-surface-1/80 rounded-xl border border-surface-3/50">
          {["", "S", "A", "B", "C", "D"].map((t) => (
            <button
              key={t}
              onClick={() => setTierFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-display font-bold transition-all ${
                tierFilter === t
                  ? "bg-accent/15 text-accent border border-accent/20"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              {t || "ALL"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="glass-card p-4 flex gap-4">
              <div className="w-8 h-8 rounded-lg shimmer" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 w-32 rounded shimmer" />
                <div className="h-2.5 w-48 rounded shimmer" />
              </div>
            </div>
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-slate-500 font-mono text-sm">
            No scored agents yet. Score an agent to see it here.
          </p>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-3/40">
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  #
                </th>
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  AGENT
                </th>
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  PLATFORM
                </th>
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  SCORE
                </th>
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  TIER
                </th>
                <th className="px-5 py-3.5 text-left text-[10px] text-slate-500 font-mono tracking-wider uppercase">
                  MAX LOAN
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr
                  key={i}
                  className="border-t border-surface-3/20 hover:bg-surface-2/30 cursor-pointer transition-colors"
                  onClick={() =>
                    (window.location.href = `/agent/${e.wallet_address}`)
                  }
                >
                  <td className="px-5 py-4 text-sm text-slate-500 font-mono">
                    {i + 1}
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-display font-semibold text-white text-sm">
                      {e.agent_name || "Unknown"}
                    </p>
                    <p className="text-[11px] text-slate-500 font-mono">
                      {e.wallet_address?.slice(0, 12)}...
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    {e.platform && <PlatformBadge platform={e.platform} />}
                  </td>
                  <td className="px-5 py-4 font-display font-extrabold text-white">
                    {e.score}
                  </td>
                  <td className="px-5 py-4">
                    <span className={`tier-badge text-xs tier-${e.tier}`}>
                      {e.tier}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-sm text-slate-400 font-mono">
                    ${e.max_loan_usdc?.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
