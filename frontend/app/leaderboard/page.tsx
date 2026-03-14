"use client";

import { useEffect, useState } from "react";
import { getLeaderboard } from "@/lib/api";
import PlatformBadge from "@/components/PlatformBadge";

const TIER_MAX: Record<string, string> = {
  S: "$500,000",
  A: "$100,000",
  B: "$25,000",
  C: "$5,000",
  D: "$1,000",
};

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

  const rankMedal = (i: number) => {
    if (i === 0) return "🥇";
    if (i === 1) return "🥈";
    if (i === 2) return "🥉";
    return i + 1;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-black text-gray-900">
            Leaderboard
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-body">
            Top AI agents ranked by on-chain credit score
          </p>
        </div>

        {/* Tier filters */}
        <div className="flex gap-1 p-1 bg-surface-1 rounded-xl border border-surface-2 shadow-sm">
          {["", "S", "A", "B", "C", "D"].map((t) => (
            <button
              key={t}
              onClick={() => setTierFilter(t)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-display font-bold transition-all ${
                tierFilter === t
                  ? `bg-accent text-white shadow-sm`
                  : "text-gray-500 hover:text-gray-800 hover:bg-surface-2"
              }`}
            >
              {t || "ALL"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="glass-card p-4 flex gap-4 items-center">
              <div className="w-8 h-8 rounded-full shimmer" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 w-36 rounded shimmer" />
                <div className="h-2.5 w-52 rounded shimmer" />
              </div>
              <div className="h-6 w-16 rounded shimmer" />
            </div>
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-20 glass-card">
          <p className="text-4xl mb-3">📊</p>
          <p className="text-gray-500 font-body text-sm">
            No scored agents yet. Score an agent to see it here.
          </p>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-2 bg-surface-1">
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">#</th>
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">Agent</th>
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">Platform</th>
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">Score</th>
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">Tier</th>
                <th className="px-5 py-3.5 text-left text-[10px] text-gray-400 font-mono tracking-widest uppercase">Max Loan</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr
                  key={i}
                  className="border-t border-surface-1 hover:bg-accent/5 cursor-pointer transition-colors group"
                  onClick={() => (window.location.href = `/agent/${e.wallet_address}`)}
                >
                  <td className="px-5 py-4 text-sm font-mono font-bold text-gray-400">
                    {rankMedal(i)}
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-display font-semibold text-gray-900 text-sm group-hover:text-accent transition-colors">
                      {e.agent_name || "Unknown Agent"}
                    </p>
                    <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                      {e.wallet_address?.slice(0, 12)}...
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    {e.platform && <PlatformBadge platform={e.platform} />}
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-xl font-display font-black text-gray-900">
                      {e.score}
                    </span>
                    <span className="text-xs text-gray-400 ml-1 font-mono">/1000</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`tier-badge text-xs tier-${e.tier}`}>{e.tier}</span>
                  </td>
                  <td className="px-5 py-4 text-sm font-mono font-semibold text-accent">
                    {TIER_MAX[e.tier] || `$${e.max_loan_usdc?.toLocaleString()}`}
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
