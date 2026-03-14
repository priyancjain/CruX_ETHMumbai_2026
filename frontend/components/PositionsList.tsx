"use client";

import { useState, useEffect } from "react";
import { getPositions } from "@/lib/api";

interface PositionsListProps {
  wallet: string;
}


const CHAIN_COLORS: Record<string, string> = {
  ethereum: "bg-blue-50 text-blue-600 border-blue-100",
  base: "bg-cyan-50 text-cyan-600 border-cyan-100",
  polygon: "bg-purple-50 text-purple-600 border-purple-100",
  arbitrum: "bg-sky-50 text-sky-600 border-sky-100",
  optimism: "bg-red-50 text-red-600 border-red-100",
  bsc: "bg-yellow-50 text-yellow-600 border-yellow-100",
  avalanche: "bg-red-50 text-red-600 border-red-100",
};

function getChainBadge(chain: string): string {
  return CHAIN_COLORS[chain?.toLowerCase()] || "bg-gray-50 text-gray-500 border-gray-200";
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
      <div className="glass-card p-6 min-h-[300px] flex flex-col justify-center items-center">
        <div className="flex gap-1 mb-4">
          {[0,1,2].map(i => (
            <div key={i} className="w-1.5 h-6 bg-[#1DB954] rounded-full animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
        <p className="text-gray-400 font-mono text-sm">Auditing assets...</p>
      </div>
    );
  }

  if (!data || data.total_count === 0) {
    return (
      <div className="glass-card p-8 text-center space-y-3">
        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto text-gray-400">
           <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/></svg>
        </div>
        <h3 className="text-sm font-display font-bold text-gray-900">Portfolio Empty</h3>
        <p className="text-gray-500 font-body text-xs max-w-xs mx-auto">
          No current token or DeFi positions detected for this wallet.
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
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <h3 className="text-[10px] text-gray-500 font-mono tracking-widest uppercase font-bold">
          PORTFOLIO POSITIONS
        </h3>
        <span className="text-[10px] text-gray-400 font-mono font-bold">
          {data.total_count} TOTAL
        </span>
      </div>

      <div className="p-6">
        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1 w-fit border border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`text-[11px] font-display font-bold px-4 py-2 rounded-lg transition-all ${
                activeTab === tab.id
                  ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-1.5 text-[10px] font-mono text-gray-400">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Position List */}
        <div className="space-y-3">
          {positions.length === 0 ? (
            <div className="py-12 text-center bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
              <p className="text-gray-400 font-mono text-xs">
                No active {activeTab} positions found.
              </p>
            </div>
          ) : (
            positions.map((pos: any, i: number) => (
              <div
                key={pos.id || i}
                className="flex items-center gap-4 bg-white border border-gray-100 rounded-xl p-4 hover:border-gray-300 hover:shadow-sm transition-all group"
              >
                {/* Token symbol mark */}
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-400 group-hover:bg-[#1DB954]/10 group-hover:text-[#1DB954] transition-colors">
                   {(pos.token_symbol || pos.protocol_name || "?").slice(0, 2).toUpperCase()}
                </div>

                {/* Token info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-display font-bold text-gray-900">
                      {pos.token_symbol || pos.protocol_name || "Unknown"}
                    </span>
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded border leading-none font-bold uppercase ${getChainBadge(
                        pos.chain
                      )}`}
                    >
                      {pos.chain || "base"}
                    </span>
                  </div>
                  {pos.protocol_name && activeTab !== "tokens" && (
                    <p className="text-[10px] text-gray-400 font-mono mt-0.5">
                      via {pos.protocol_name}
                    </p>
                  )}
                </div>

                {/* Balance */}
                <div className="text-right">
                  <p className="text-sm font-mono font-bold text-gray-900">
                    {formatUSD(pos.balance_usd)}
                  </p>
                  {pos.balance_raw && pos.balance_raw !== "0" && (
                    <p className="text-[10px] text-gray-400 font-mono">
                      {Number(pos.balance_raw).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                    </p>
                  )}
                </div>

                {/* APY for staking/defi */}
                {pos.apy != null && pos.apy > 0 && (
                  <div className="text-right ml-2 pl-4 border-l border-gray-100">
                    <div className="px-2 py-1 bg-emerald-50 text-[#1DB954] rounded-lg">
                       <p className="text-[10px] font-mono font-bold">
                        +{(pos.apy * 100).toFixed(1)}% APY
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}
