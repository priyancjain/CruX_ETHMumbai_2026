"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  requestScore,
  discoverAgents,
  discoverAllAgents,
  getStats,
  getPlatforms,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";
import AgentCard from "@/components/AgentCard";
import PlatformTabs from "@/components/PlatformTabs";

export default function Home() {
  const router = useRouter();

  const [wallet, setWallet] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [platform, setPlatform] = useState("virtuals");
  const [agents, setAgents] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [browseLoading, setBrowseLoading] = useState(true);

  const [stats, setStats] = useState<any>(null);
  const [platformCounts, setPlatformCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
    getPlatforms()
      .then((platforms: any[]) => {
        const counts: Record<string, number> = {};
        for (const p of platforms) {
          if (p.name && p.total_agents) counts[p.name] = p.total_agents;
        }
        setPlatformCounts(counts);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadAgents();
  }, [platform, page]);

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
    if (!wallet || !wallet.startsWith("0x") || wallet.length !== 42) {
      setSearchError("Enter a valid EVM wallet address (0x...)");
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
    <div className="space-y-10">
      {/* ── Hero ───────────────────────────────────── */}
      <section className="pt-10 pb-2 text-center space-y-4">
        <h1 className="font-display text-5xl md:text-6xl font-extrabold tracking-tight">
          <span className="text-gradient">AgentScore</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto leading-relaxed">
          Universal credit rating for AI agents. Browse, analyze, and score
          autonomous agents across every platform.
        </p>

        {/* Search */}
        <form onSubmit={handleSearch} className="max-w-lg mx-auto pt-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              </div>
              <input
                type="text"
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                placeholder="Paste wallet address (0x...)"
                className="w-full pl-10 pr-4 py-3 bg-surface-1 border border-surface-3/60 rounded-xl text-white text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-accent/40 focus:shadow-glow transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={searchLoading}
              className="px-5 py-3 bg-accent/15 hover:bg-accent/25 border border-accent/20 text-accent rounded-xl text-sm font-display font-bold tracking-wide transition-all disabled:opacity-40"
            >
              {searchLoading ? "..." : "SCORE"}
            </button>
          </div>
          {searchError && (
            <p className="text-red-400 mt-2 text-xs font-mono">{searchError}</p>
          )}
          {searchLoading && (
            <p className="text-accent/70 mt-2 text-xs font-mono animate-pulse">
              Scoring in progress &mdash; analyzing onchain data...
            </p>
          )}
        </form>
      </section>

      {/* ── Stats ──────────────────────────────────── */}
      {stats && (
        <div className="flex justify-center gap-3">
          {[
            { value: stats.total_agents?.toLocaleString() || "0", label: "Agents" },
            { value: stats.scored_agents?.toLocaleString() || "0", label: "Scored" },
            { value: stats.avg_score || "0", label: "Avg Score" },
          ].map((s) => (
            <div
              key={s.label}
              className="glass-card px-5 py-3 text-center min-w-[100px]"
            >
              <p className="text-xl font-display font-extrabold text-accent">
                {s.value}
              </p>
              <p className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mt-0.5">
                {s.label}
              </p>
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="glass-card p-5 space-y-3">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-xl shimmer" />
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 w-24 rounded shimmer" />
                  <div className="h-2.5 w-32 rounded shimmer" />
                </div>
              </div>
              <div className="h-8 w-full rounded shimmer" />
              <div className="h-3 w-20 rounded shimmer" />
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-children">
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
        <div className="flex items-center justify-center gap-3 pb-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 glass-card text-sm font-mono text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            &larr; PREV
          </button>
          <span className="text-xs text-slate-500 font-mono px-3">
            {page}
            {totalPages > 0 && totalPages !== -1 ? ` / ${totalPages}` : ""}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={totalPages > 0 && page >= totalPages}
            className="px-4 py-2 glass-card text-sm font-mono text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            NEXT &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
