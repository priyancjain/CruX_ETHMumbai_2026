"use client";

import { useState, useEffect } from "react";
import { getTransactions } from "@/lib/api";

interface TransactionTableProps {
  wallet: string;
}


const TYPE_COLORS: Record<string, string> = {
  swap: "bg-blue-50 text-blue-600 border-blue-200",
  transfer: "bg-emerald-50 text-emerald-600 border-emerald-200",
  approve: "bg-amber-50 text-amber-600 border-amber-200",
  mint: "bg-purple-50 text-purple-600 border-purple-200",
  stake: "bg-teal-50 text-teal-600 border-teal-200",
  default: "bg-gray-50 text-gray-600 border-gray-200",
};

function getTypeBadge(type: string | null): string {
  if (!type) return TYPE_COLORS.default;
  const lower = type.toLowerCase();
  for (const [key, cls] of Object.entries(TYPE_COLORS)) {
    if (lower.includes(key)) return cls;
  }
  return TYPE_COLORS.default;
}

function formatValue(tx: any): React.ReactNode {
  const val_usd = tx.value_usd;
  const val_raw = tx.value_raw;
  const symbol = tx.token_symbol || "ETH";

  // If we have a USD value, prioritize it for "Decision Making"
  if (val_usd && val_usd > 0) {
    return (
      <div className="text-right">
        <p className="font-mono text-[11px] font-black text-gray-900">
          ${val_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        <p className="text-[9px] text-gray-400 font-mono uppercase">USD VALUE</p>
      </div>
    );
  }

  // Fallback to raw token amount
  if (val_raw && val_raw !== "0") {
    const num = parseFloat(val_raw);
    if (isNaN(num)) return <span className="text-gray-300">-</span>;
    
    // Most Alchemy values are already decimal-adjusted. If > 1e12, it's probably wei.
    const isWei = num > 1_000_000_000_000;
    const adjustedNum = isWei ? num / 1e18 : num;
    
    const formattedNum = adjustedNum < 0.0001 
      ? adjustedNum.toExponential(2) 
      : adjustedNum.toLocaleString(undefined, { maximumFractionDigits: 6 });

    return (
      <div className="text-right">
        <p className="font-mono text-[11px] font-black text-gray-900">
          {formattedNum} <span className="text-[9px] text-gray-400 font-bold ml-0.5">{symbol}</span>
        </p>
        <p className="text-[9px] text-gray-400 font-mono uppercase">AMOUNT</p>
      </div>
    );
  }

  return <span className="text-gray-300">-</span>;
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
  
  // Filters
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [assetFilter, setAssetFilter] = useState<string | null>(null);
  const [chainFilter, setChainFilter] = useState<string | null>(null);
  const [showTypeDropdown, setShowTypeDropdown] = useState(false);
  const [showAssetDropdown, setShowAssetDropdown] = useState(false);
  const [showChainDropdown, setShowChainDropdown] = useState(false);

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

  const uniqueTypes = Array.from(new Set(transactions.map(tx => tx.tx_type || "unknown"))).sort();
  const uniqueAssets = Array.from(new Set(transactions.map(tx => tx.token_symbol || "ETH"))).sort();
  const uniqueChains = Array.from(new Set(transactions.map(tx => tx.chain || "base"))).sort();

  const filteredTransactions = transactions.filter(tx => {
    const matchesType = !typeFilter || tx.tx_type === typeFilter;
    const matchesAsset = !assetFilter || (tx.token_symbol || "ETH") === assetFilter;
    const matchesChain = !chainFilter || (tx.chain || "base") === chainFilter;
    return matchesType && matchesAsset && matchesChain;
  });

  const totalPages = Math.ceil(total / pageSize);

  const FilterDropdown = ({ 
    label, 
    options, 
    value, 
    onChange, 
    isOpen, 
    setIsOpen 
  }: { 
    label: string, 
    options: string[], 
    value: string | null, 
    onChange: (val: string | null) => void,
    isOpen: boolean,
    setIsOpen: (open: boolean) => void
  }) => (
    <div className="relative inline-block ml-1">
      <button 
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={`hover:text-gray-900 transition-colors ${value ? 'text-[#1DB954]' : 'text-gray-400'}`}
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
        </svg>
      </button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)}></div>
          <div className="absolute left-0 mt-2 w-32 bg-white border border-gray-100 rounded-lg shadow-xl z-20 py-1 overflow-hidden animate-in fade-in zoom-in duration-200">
            <button 
              onClick={() => { onChange(null); setIsOpen(false); }}
              className="w-full text-left px-3 py-1.5 text-[10px] hover:bg-gray-50 font-mono text-gray-500 uppercase flex items-center justify-between"
            >
              All {label}s
              {!value && <span className="w-1 h-1 rounded-full bg-[#1DB954]" />}
            </button>
            <div className="h-[1px] bg-gray-100 my-1" />
            {options.map(opt => (
              <button 
                key={opt}
                onClick={() => { onChange(opt); setIsOpen(false); }}
                className="w-full text-left px-3 py-1.5 text-[10px] hover:bg-gray-50 font-mono text-gray-900 flex items-center justify-between"
              >
                {opt.toUpperCase()}
                {value === opt && <span className="w-1 h-1 rounded-full bg-[#1DB954]" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );

  if (loading && transactions.length === 0) {
    return (
      <div className="glass-card p-6 min-h-[400px] flex flex-col justify-center items-center">
        <div className="flex gap-1 mb-4">
          {[0,1,2].map(i => (
            <div key={i} className="w-1.5 h-6 bg-[#1DB954] rounded-full animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
        <p className="text-gray-400 font-mono text-sm">Fetching on-chain activity...</p>
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="glass-card p-8 text-center space-y-3">
        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto text-gray-400">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7"/><path d="M16 19h6"/><path d="M19 16v6"/><circle cx="12" cy="12" r="3"/></svg>
        </div>
        <h3 className="text-sm font-display font-bold text-gray-900">No Transactions Detected</h3>
        <p className="text-gray-500 font-body text-xs max-w-xs mx-auto">
          We couldn't find any recent on-chain transactions for this wallet on Base.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
        <h3 className="text-[10px] text-gray-500 font-mono tracking-widest uppercase font-bold">
          TRANSACTION HISTORY
        </h3>
        <div className="flex items-center gap-3">
          {(typeFilter || assetFilter || chainFilter) && (
            <button 
              onClick={() => { setTypeFilter(null); setAssetFilter(null); setChainFilter(null); }}
              className="text-[9px] text-[#1DB954] font-mono font-bold hover:underline bg-[#1DB954]/5 px-2 py-0.5 rounded border border-[#1DB954]/20"
            >
              CLEAR FILTERS
            </button>
          )}
          <span className="text-[10px] text-gray-400 font-mono px-2 py-0.5 bg-white border border-gray-200 rounded">
            {total} SIGNALS
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-[9px] text-gray-400 font-mono bg-gray-50/50 border-b border-gray-100 uppercase tracking-widest">
              <th className="text-left py-4 px-6 font-black">
                <div className="flex items-center">
                  Transfer Type
                  <FilterDropdown 
                    label="Type" 
                    options={uniqueTypes} 
                    value={typeFilter} 
                    onChange={setTypeFilter} 
                    isOpen={showTypeDropdown} 
                    setIsOpen={setShowTypeDropdown} 
                  />
                </div>
              </th>
              <th className="text-left py-4 px-4 font-black">
                <div className="flex items-center">
                  Asset
                  <FilterDropdown 
                    label="Asset" 
                    options={uniqueAssets} 
                    value={assetFilter} 
                    onChange={setAssetFilter} 
                    isOpen={showAssetDropdown} 
                    setIsOpen={setShowAssetDropdown} 
                  />
                </div>
              </th>
              <th className="text-right py-4 px-4 font-black">Amount / Value</th>
              <th className="text-left py-4 px-4 font-black">Counterparty</th>
              <th className="text-left py-4 px-4 font-black">Protocol</th>
              <th className="text-center py-4 px-4 font-black">
                <div className="flex items-center justify-center">
                  Network
                  <FilterDropdown 
                    label="Network" 
                    options={uniqueChains} 
                    value={chainFilter} 
                    onChange={setChainFilter} 
                    isOpen={showChainDropdown} 
                    setIsOpen={setShowChainDropdown} 
                  />
                </div>
              </th>
              <th className="text-right py-4 px-6 font-black">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredTransactions.map((tx, i) => {
              const peer = tx.peer_address || (tx.is_incoming ? tx.from_address : tx.to_address);
              return (
                <tr
                  key={tx.id || i}
                  className="hover:bg-gray-50/80 transition-colors group"
                >
                  <td className="py-4 px-6">
                    <span
                      className={`text-[9px] font-mono px-2 py-0.5 rounded border leading-none inline-block font-bold tracking-tight ${getTypeBadge(
                        tx.tx_type
                      )}`}
                    >
                      {(tx.tx_type || "unknown").toUpperCase()}
                    </span>
                  </td>
                  <td className="py-4 px-4 font-mono text-xs text-gray-900 font-medium">
                    {tx.token_symbol || "ETH"}
                  </td>
                  <td className="py-4 px-4 font-mono text-xs text-right text-gray-900">
                    {formatValue(tx)}
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                        tx.is_incoming ? 'bg-emerald-50 text-emerald-500' : 'bg-gray-100 text-gray-400'
                      }`}>
                        {tx.is_incoming ? (
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m7 7 10 10"/><path d="M17 7v10H7"/></svg>
                        ) : (
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>
                        )}
                      </div>
                      <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${
                        tx.is_incoming ? 'text-emerald-600 bg-emerald-50/50' : 'text-gray-500 bg-gray-100/50'
                      }`}>
                        {shortenAddr(peer)}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-gray-400">
                    {tx.protocol_name ? (
                       <span className="text-gray-700 font-medium">{tx.protocol_name}</span>
                    ) : (
                      <span className="opacity-40">-</span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-center">
                    <span className="text-[10px] font-mono text-gray-400 border border-gray-200 px-1.5 py-0.5 rounded bg-white shadow-sm capitalize">
                      {tx.chain || "base"}
                    </span>
                  </td>
                  <td className="py-4 px-6 font-mono text-[11px] text-gray-500 text-right">
                    {tx.timestamp
                      ? new Date(tx.timestamp).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })
                      : "PENDING"}
                  </td>
                </tr>
              );
            })}
            {filteredTransactions.length === 0 && (
              <tr>
                <td colSpan={7} className="py-20 text-center">
                  <p className="text-gray-400 font-mono text-xs italic">No transactions match the selected filters.</p>
                  <button 
                    onClick={() => { setTypeFilter(null); setAssetFilter(null); setChainFilter(null); }}
                    className="mt-4 text-[10px] text-[#1DB954] font-mono font-bold hover:underline"
                  >
                    RESET FILTERS
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-4 bg-gray-50/30 border-t border-gray-100">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-[11px] font-mono font-bold text-gray-500 hover:text-gray-900 disabled:opacity-30 border border-gray-200 rounded-lg bg-white transition-all shadow-sm"
          >
            ← PREV
          </button>
          <span className="text-[10px] font-mono text-gray-400 font-bold">
            PAGE {page} <span className="mx-1 text-gray-200">/</span> {totalPages}
          </span>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-[11px] font-mono font-bold text-gray-500 hover:text-gray-900 disabled:opacity-30 border border-gray-200 rounded-lg bg-white transition-all shadow-sm"
          >
            NEXT →
          </button>
        </div>
      )}
    </div>
  );
}


