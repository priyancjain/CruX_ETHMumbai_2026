"use client";

import { useState, useEffect } from "react";
import { getTransactions } from "@/lib/api";

interface TransactionTableProps {
  wallet: string;
}

const TYPE_COLORS: Record<string, string> = {
  swap: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  transfer: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  approve: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  mint: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  stake: "bg-teal-500/15 text-teal-400 border-teal-500/20",
  default: "bg-slate-500/15 text-slate-400 border-slate-500/20",
};

function getTypeBadge(type: string | null): string {
  if (!type) return TYPE_COLORS.default;
  const lower = type.toLowerCase();
  for (const [key, cls] of Object.entries(TYPE_COLORS)) {
    if (lower.includes(key)) return cls;
  }
  return TYPE_COLORS.default;
}

function formatValue(value: number | null): string {
  if (!value || value === 0) return "-";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

function shortenAddr(addr: string | null): string {
  if (!addr) return "-";
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export default function TransactionTable({ wallet }: TransactionTableProps) {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const pageSize = 10;

  useEffect(() => {
    loadTransactions();
  }, [wallet, page]);

  async function loadTransactions() {
    setLoading(true);
    try {
      const data = await getTransactions(wallet, page, pageSize);
      setTransactions(data.transactions || []);
      setTotal(data.total || 0);
    } catch {
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  if (loading && transactions.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
          TRANSACTION HISTORY
        </h3>
        <p className="text-slate-500 font-mono text-sm animate-pulse">
          Loading transactions...
        </p>
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
          TRANSACTION HISTORY
        </h3>
        <p className="text-slate-500 font-mono text-sm">
          No transaction data available. Score the agent to fetch HeyElsa data.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase">
          TRANSACTION HISTORY
        </h3>
        <span className="text-[10px] text-slate-600 font-mono">
          {total} total
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] text-slate-500 font-mono border-b border-surface-3/30">
              <th className="text-left pb-2 pr-3">TYPE</th>
              <th className="text-left pb-2 pr-3">TOKEN</th>
              <th className="text-right pb-2 pr-3">VALUE</th>
              <th className="text-left pb-2 pr-3">FROM / TO</th>
              <th className="text-left pb-2 pr-3">PROTOCOL</th>
              <th className="text-left pb-2 pr-3">CHAIN</th>
              <th className="text-right pb-2">TIME</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => (
              <tr
                key={tx.id || i}
                className="border-b border-surface-3/15 hover:bg-surface-2/30 transition-colors"
              >
                <td className="py-2 pr-3">
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getTypeBadge(
                      tx.tx_type
                    )}`}
                  >
                    {(tx.tx_type || "unknown").toUpperCase()}
                  </span>
                </td>
                <td className="py-2 pr-3 font-mono text-slate-300">
                  {tx.token_symbol || "-"}
                </td>
                <td className="py-2 pr-3 font-mono text-right text-slate-200">
                  {formatValue(tx.value_usd)}
                </td>
                <td className="py-2 pr-3 font-mono text-slate-500 text-[11px]">
                  {tx.is_incoming ? (
                    <span className="text-emerald-400">
                      {shortenAddr(tx.from_address)}
                    </span>
                  ) : (
                    <span className="text-slate-400">
                      {shortenAddr(tx.to_address)}
                    </span>
                  )}
                </td>
                <td className="py-2 pr-3 font-mono text-slate-400 text-[11px]">
                  {tx.protocol_name || "-"}
                </td>
                <td className="py-2 pr-3">
                  <span className="text-[10px] font-mono text-slate-500 bg-surface-2/60 px-1.5 py-0.5 rounded">
                    {tx.chain || "base"}
                  </span>
                </td>
                <td className="py-2 font-mono text-[11px] text-slate-500 text-right">
                  {tx.timestamp
                    ? new Date(tx.timestamp).toLocaleDateString()
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="text-[11px] font-mono text-slate-400 hover:text-accent disabled:opacity-30 transition-colors"
          >
            PREV
          </button>
          <span className="text-[10px] font-mono text-slate-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="text-[11px] font-mono text-slate-400 hover:text-accent disabled:opacity-30 transition-colors"
          >
            NEXT
          </button>
        </div>
      )}
    </div>
  );
}
