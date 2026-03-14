"use client";

import { useState, useEffect } from "react";
import { getPositions } from "@/lib/api";

interface PositionsListProps {
  wallet: string;
}

const CHAIN_COLORS: Record<string, string> = {
  ethereum: "bg-blue-500/15 text-blue-400",
  base: "bg-blue-600/15 text-blue-300",
  polygon: "bg-purple-500/15 text-purple-400",
  arbitrum: "bg-sky-500/15 text-sky-400",
  optimism: "bg-red-500/15 text-red-400",
  bsc: "bg-yellow-500/15 text-yellow-400",
  avalanche: "bg-red-600/15 text-red-300",
};

function getChainColor(chain: string): string {
  return CHAIN_COLORS[chain?.toLowerCase()] || "bg-slate-500/15 text-slate-400";
}

function formatUSD(value: number): string {
  if (!value || value === 0) return "$0.00";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

export default function PositionsList({ wallet }: PositionsListProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"tokens" | "defi" | "staking">(
    "tokens"
  );

  useEffect(() => {
    loadPositions();
  }, [wallet]);

  async function loadPositions() {
    try {
      const result = await getPositions(wallet);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
          PORTFOLIO POSITIONS
        </h3>
        <p className="text-slate-500 font-mono text-sm animate-pulse">
          Loading positions...
        </p>
      </div>
    );
  }

  if (!data || data.total_count === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
          PORTFOLIO POSITIONS
        </h3>
        <p className="text-slate-500 font-mono text-sm">
          No position data available. Score the agent to fetch HeyElsa data.
        </p>
      </div>
    );
  }

  const tabs = [
    { id: "tokens" as const, label: "Tokens", count: data.tokens?.length || 0 },
    { id: "defi" as const, label: "DeFi", count: data.defi?.length || 0 },
    { id: "staking" as const, label: "Staking", count: data.staking?.length || 0 },
  ];

  const positions = data[activeTab] || [];

  return (
    <div className="glass-card p-6">
      <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
        PORTFOLIO POSITIONS
      </h3>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-surface-2/40 rounded-lg p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-[11px] font-mono px-3 py-1.5 rounded-md transition-all ${
              activeTab === tab.id
                ? "bg-accent/15 text-accent border border-accent/20"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1 text-[9px] opacity-60">({tab.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Position List */}
      <div className="space-y-2">
        {positions.length === 0 ? (
          <p className="text-slate-500 font-mono text-sm py-4">
            No {activeTab} positions found.
          </p>
        ) : (
          positions.map((pos: any, i: number) => (
            <div
              key={pos.id || i}
              className="flex items-center gap-3 bg-surface-2/30 border border-surface-3/20 rounded-lg p-3 hover:bg-surface-2/50 transition-colors"
            >
              {/* Token info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono font-medium text-slate-200">
                    {pos.token_symbol || pos.protocol_name || "Unknown"}
                  </span>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${getChainColor(
                      pos.chain
                    )}`}
                  >
                    {pos.chain || "base"}
                  </span>
                </div>
                {pos.protocol_name && activeTab !== "tokens" && (
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                    via {pos.protocol_name}
                  </p>
                )}
              </div>

              {/* Balance */}
              <div className="text-right">
                <p className="text-sm font-mono font-medium text-slate-200">
                  {formatUSD(pos.balance_usd)}
                </p>
                {pos.balance_raw && pos.balance_raw !== "0" && (
                  <p className="text-[10px] text-slate-500 font-mono">
                    {Number(pos.balance_raw).toFixed(4)}
                  </p>
                )}
              </div>

              {/* APY for staking/defi */}
              {pos.apy != null && pos.apy > 0 && (
                <div className="text-right ml-2">
                  <p className="text-[10px] text-emerald-400 font-mono">
                    {(pos.apy * 100).toFixed(1)}% APY
                  </p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
