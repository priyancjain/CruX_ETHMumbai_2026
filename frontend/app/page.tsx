"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  requestScore,
  discoverAgents,
  discoverAllAgents,
  getStats,
  getPlatforms,
  searchAgents,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";
import AgentCard from "@/components/AgentCard";
import PlatformTabs from "@/components/PlatformTabs";

const NAMES = [
  "Score.",
  "Trust.",
  "Cred.",
  "Rank.",
  "Pulse."
];

export default function Home() {
  const router = useRouter();

  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"name" | "wallet">("name");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [isSearchResults, setIsSearchResults] = useState(false);

  // Animation states
  const [nameIndex, setNameIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setNameIndex((prev) => (prev + 1) % NAMES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const [platform, setPlatform] = useState("virtuals");
  const [agents, setAgents] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [browseLoading, setBrowseLoading] = useState(true);

  const [stats, setStats] = useState<any>(null);
  const [platformCounts, setPlatformCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    getStats().then(setStats).catch(() => { });
    getPlatforms()
      .then((platforms: any[]) => {
        const counts: Record<string, number> = {};
        for (const p of platforms) {
          if (p.name && p.total_agents) counts[p.name] = p.total_agents;
        }
        setPlatformCounts(counts);
      })
      .catch(() => { });
  }, []);

  useEffect(() => {
    // Only reload agents if not showing search results
    if (!isSearchResults) {
      loadAgents();
    }
  }, [platform, page, isSearchResults]);

  async function loadAgents() {
    setBrowseLoading(true);
    try {
      let data;
      if (platform === "all") {
        data = await discoverAllAgents(page, 20);
      } else {
        data = await discoverAgents(platform, page, 50);
      }
      setAgents(data.agents || []);
      const tp = data.total_pages;
      if (tp && tp > 0) {
        setTotalPages(tp);
      } else {
        const total = data.total || data.agents?.length || 0;
        const ps = data.page_size || 50;
        setTotalPages(Math.max(1, Math.ceil(total / ps)));
      }
      // Update platform counts from live API data
      if (platform === "all" && data.platform_totals) {
        setPlatformCounts((prev) => ({ ...prev, ...data.platform_totals }));
      } else if (platform !== "all" && data.total) {
        setPlatformCounts((prev) => ({ ...prev, [platform]: data.total }));
      }
    } catch {
      setAgents([]);
      setTotalPages(1);
    } finally {
      setBrowseLoading(false);
    }
  }

  function handleTabChange(newPlatform: string) {
    setPlatform(newPlatform);
    setPage(1);
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();

    if (searchMode === "name") {
      if (!searchQuery.trim() || searchQuery.trim().length < 2) {
        setSearchError("Enter at least 2 characters to search.");
        return;
      }
      setSearchLoading(true);
      setSearchError("");
      try {
        const res = await searchAgents(searchQuery.trim());
        const found = res.agents || [];
        setAgents(found);
        setIsSearchResults(true);
        if (found.length === 0) {
          setSearchError(`No agents found for "${searchQuery}". Try a different name, purpose or platform.`);
        }
      } catch (err: any) {
        setSearchError(err.message || "Search failed");
      } finally {
        setSearchLoading(false);
      }
      return;
    }

    // Wallet Mode Scoring Flow
    const wallet = searchQuery.trim();
    if (!wallet || wallet.length < 30) {
      setSearchError("Enter a valid agent address (EVM 0x... or Cosmos fetch1...)");
      return;
    }
    setSearchLoading(true);
    setSearchError("");
    try {
      const result = await requestScore(wallet);
      if (result.cached || result.score !== undefined) {
        router.push(`/agent/${wallet}`);
        return;
      }
      const channel = supabase
        .channel(`score:${wallet}`)
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "scores",
            filter: `wallet_address=eq.${wallet}`,
          },
          () => {
            supabase.removeChannel(channel);
            router.push(`/agent/${wallet}`);
          }
        )
        .subscribe();
      setTimeout(() => {
        supabase.removeChannel(channel);
        setSearchLoading(false);
        router.push(`/agent/${wallet}`);
      }, 120000);
    } catch (err: any) {
      setSearchError(err.message || "Failed to request score");
      setSearchLoading(false);
    }
  }

  return (
    <div className="space-y-12 overflow-hidden">

      {/* ── Hero ── */}
      <section className="pt-14 pb-6 flex flex-col items-center text-center">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex items-center justify-center gap-2 mb-5"
        >
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#1DB954]/40 bg-[#1DB954]/08 text-[#1DB954] text-[11px] font-mono font-semibold tracking-wider uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1DB954] animate-pulse" />
            On-Chain Credit Rating
          </span>
          <span className="text-[11px] font-mono text-gray-400">BASE · ETH Mumbai 2026</span>
        </motion.div>

        {/* Main headline — center-aligned, editorial */}
        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
          className="font-display text-6xl md:text-8xl font-black tracking-tight text-gray-900 leading-[0.95] mb-6 flex flex-col items-center"
        >
          <span>Agent</span>
          <div className="h-[72px] md:h-[110px] overflow-hidden relative w-full flex justify-center">
            <AnimatePresence mode="popLayout">
              <motion.span
                key={NAMES[nameIndex]}
                initial={{ y: 80, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -80, opacity: 0 }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
                className="text-[#1DB954] absolute"
              >
                {NAMES[nameIndex]}
              </motion.span>
            </AnimatePresence>
          </div>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
          className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed font-body mb-8"
        >
          Universal credit infrastructure for autonomous AI agents.
          Browse, score, and underwrite agents across every platform
          using live on-chain behavioral data.
        </motion.p>

        {/* Search card — terminal style */}
        <div className="w-full max-w-2xl">
          {/* Mode toggle */}
          <div className="flex gap-0 mb-0 border border-[#e0e0e0] rounded-t-xl overflow-hidden bg-[#f5f5f5]">
            <button
              type="button"
              onClick={() => { setSearchMode("name"); setSearchError(""); }}
              className={`flex-1 py-2.5 font-mono text-xs font-semibold tracking-widest uppercase transition-all border-r border-[#e0e0e0] ${searchMode === "name"
                ? "bg-white text-[#1DB954] border-b-2 border-b-[#1DB954]"
                : "text-gray-400 hover:text-gray-700 hover:bg-white/60"
                }`}
            >
              Search by Name / Purpose
            </button>
            <button
              type="button"
              onClick={() => { setSearchMode("wallet"); setSearchError(""); }}
              className={`flex-1 py-2.5 font-mono text-xs font-semibold tracking-widest uppercase transition-all ${searchMode === "wallet"
                ? "bg-white text-[#1DB954] border-b-2 border-b-[#1DB954]"
                : "text-gray-400 hover:text-gray-700 hover:bg-white/60"
                }`}
            >
              ⚡ Score by Wallet ID
            </button>
          </div>

          {/* Input row */}
          <form onSubmit={handleSearch}>
            <div className="flex border border-t-0 border-[#e0e0e0] rounded-b-xl overflow-hidden bg-white shadow-sm">
              <div className="relative flex-1">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSearchError("");
                    if (e.target.value === "") {
                      setIsSearchResults(false);
                      loadAgents();
                    }
                  }}
                  placeholder={searchMode === "name"
                    ? "DeFi trading, arbitrage, NFT minting, any purpose..."
                    : "0x Paste wallet address to score..."
                  }
                  className="w-full pl-10 pr-4 py-4 bg-transparent text-gray-900 text-sm font-mono placeholder-gray-400 focus:outline-none transition-all"
                />
              </div>
              <button
                type="submit"
                disabled={searchLoading}
                className="px-8 py-4 bg-[#1DB954] hover:bg-[#17a348] text-white font-display font-bold text-sm tracking-wide transition-all disabled:opacity-50 border-l border-[#e0e0e0]"
              >
                {searchLoading ? "···" : (searchMode === "name" ? "SEARCH" : "SCORE")}
              </button>
            </div>

            {searchError && (
              <p className="text-[#FF3B30] text-xs font-mono mt-2 flex items-center gap-1">
                <span>⚠</span> {searchError}
              </p>
            )}
            {searchLoading && searchMode === "wallet" && (
              <p className="text-[#1DB954] mt-2 text-xs font-mono animate-pulse">
                ► Scoring in progress — analyzing on-chain transactions...
              </p>
            )}
          </form>

          {/* Clear search banner */}
          {isSearchResults && (
            <div className="mt-3 flex items-center justify-between px-4 py-2 bg-[#1DB954]/08 border border-[#1DB954]/30 rounded-lg">
              <span className="text-xs text-[#1DB954] font-mono font-semibold">
                ✓ Results for &ldquo;{searchQuery}&rdquo;
              </span>
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSearchError("");
                  setIsSearchResults(false);
                  loadAgents();
                }}
                className="text-xs text-gray-400 hover:text-[#FF3B30] font-mono ml-4 transition-colors"
              >
                Clear ×
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ── Stats row — DM Mono terminal readouts ── */}
      {stats && (
        <div className="grid grid-cols-3 gap-0 border border-[#e0e0e0] rounded-xl overflow-hidden">
          {[
            { value: stats.total_agents?.toLocaleString() || "0", label: "Agents Indexed", color: "text-gray-900" },
            { value: stats.scored_agents?.toLocaleString() || "0", label: "Scored", color: "text-[#1DB954]" },
            { value: stats.avg_score || "0", label: "Avg Score / 1000", color: "text-[#007AFF]" },
          ].map((s, i) => (
            <div
              key={s.label}
              className={`bg-white px-6 py-5 ${i < 2 ? "border-r border-[#e0e0e0]" : ""
                }`}
            >
              <p className={`stat-number ${s.color}`}>{s.value}</p>
              <p className="terminal-label mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Platform Tabs ──────────────────────────── */}
      <div className="flex items-center justify-between">
        <PlatformTabs active={platform} onSelect={handleTabChange} counts={platformCounts} />
        <span className="text-[11px] text-slate-600 font-mono hidden md:block">
          {browseLoading ? "LOADING..." : `${agents.length} agents`}
        </span>
      </div>

      {/* ── Agent Grid ─────────────────────────────── */}
      {browseLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="glass-card overflow-hidden">
              <div className="h-1 bg-gray-200 rounded-t-xl" />
              <div className="p-6 space-y-4">
                <div className="flex gap-4">
                  <div className="w-14 h-14 rounded-xl shimmer flex-shrink-0" />
                  <div className="flex-1 space-y-2.5 pt-1">
                    <div className="h-4 w-28 rounded shimmer" />
                    <div className="h-3 w-36 rounded shimmer" />
                    <div className="h-5 w-16 rounded shimmer" />
                  </div>
                </div>
                <div className="h-8 w-full rounded shimmer" />
                <div className="h-3 w-24 rounded shimmer" />
              </div>
            </div>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-slate-500 font-mono text-sm">
            No agents found. Try a different platform.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children">
          {agents.map((agent, i) => (
            <AgentCard
              key={`${agent.wallet_address}-${i}`}
              wallet_address={agent.wallet_address}
              agent_name={agent.agent_name}
              description={agent.description}
              platform={agent.platform}
              score={agent.score}
              tier={agent.tier}
              mcap_usd={agent.mcap_usd}
              holder_count={agent.holder_count}
              image_url={agent.image_url}
              is_evm_wallet={agent.is_evm_wallet}
              chain={agent.chain}
            />
          ))}
        </div>
      )}

      {/* ── Pagination ─────────────────────────────── */}
      {!browseLoading && agents.length > 0 && (
        <div className="flex items-center justify-center gap-3 pb-10">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-5 py-2.5 bg-white border border-gray-200 text-sm font-display font-semibold text-gray-600 hover:text-gray-900 hover:border-gray-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-400 font-mono px-4 py-2 bg-gray-100 rounded-lg">
            {page}{totalPages > 0 && totalPages !== -1 ? ` / ${totalPages}` : ""}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={totalPages > 0 && page >= totalPages}
            className="px-5 py-2.5 bg-white border border-gray-200 text-sm font-display font-semibold text-gray-600 hover:text-gray-900 hover:border-gray-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
