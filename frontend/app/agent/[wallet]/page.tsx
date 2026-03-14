"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { getAgent, getScoreHistory, requestScore } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import ScoreCard from "@/components/ScoreCard";
import FeatureRadar from "@/components/FeatureRadar";
import ScoreHistory from "@/components/ScoreHistory";
import PlatformBadge from "@/components/PlatformBadge";
import PnLCard from "@/components/PnLCard";
import TransactionTable from "@/components/TransactionTable";
import PositionsList from "@/components/PositionsList";

type Tab = "overview" | "transactions" | "positions";

export default function AgentPage() {
  const params = useParams();
  const wallet = params.wallet as string;

  const [agent, setAgent] = useState<any>(null);
  const [score, setScore] = useState<any>(null);
  const [features, setFeatures] = useState<any>(null);
  const [pnl, setPnl] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Track the score ID at the moment we start polling, so we detect NEW scores
  const scoreIdBeforePolling = useRef<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up polling interval
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Start polling — uses ref-based comparison instead of stale closure
  const startPolling = useCallback(() => {
    stopPolling(); // clear any existing interval first
    let attempts = 0;

    pollIntervalRef.current = setInterval(async () => {
      attempts++;
      if (attempts > 60) {
        stopPolling();
        setScoring(false);
        return;
      }
      try {
        const data = await getAgent(wallet).catch(() => null);
        if (
          data?.latest_score &&
          data.latest_score.id !== scoreIdBeforePolling.current
        ) {
          // New score arrived — update everything and stop polling
          stopPolling();
          setAgent(data.agent);
          setScore(data.latest_score);
          setFeatures(data.features);
          setPnl(data.pnl);
          setScoring(false);
          const hist = await getScoreHistory(wallet).catch(() => ({
            scores: [],
          }));
          setHistory(hist.scores || []);
        }
      } catch {
        // keep polling
      }
    }, 3000);
  }, [wallet, stopPolling]);

  // Cleanup on unmount or wallet change
  useEffect(() => {
    return () => stopPolling();
  }, [wallet, stopPolling]);

  useEffect(() => {
    loadData();

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
        (payload) => {
          stopPolling();
          setScore(payload.new);
          setScoring(false);
          loadData();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      stopPolling();
    };
  }, [wallet]);

  async function loadData() {
    try {
      const [agentData, historyData] = await Promise.all([
        getAgent(wallet).catch(() => null),
        getScoreHistory(wallet).catch(() => ({ scores: [] })),
      ]);

      if (agentData) {
        setAgent(agentData.agent);
        setScore(agentData.latest_score);
        setFeatures(agentData.features);
        setPnl(agentData.pnl);
      }
      setHistory(historyData.scores || []);

      // If no score exists, ALWAYS call requestScore (backend handles dedup + stale cleanup)
      if (!agentData?.latest_score) {
        try {
          scoreIdBeforePolling.current = null;
          console.log("[AgentPage] No score found — requesting scoring for", wallet);
          await requestScore(wallet);
          setScoring(true);
          startPolling();
        } catch (err) {
          console.error("[AgentPage] requestScore failed:", err);
        }
      }
      // If score exists — just display, no polling needed
    } catch (err) {
      console.error("[AgentPage] loadData failed:", err);
      try {
        scoreIdBeforePolling.current = null;
        await requestScore(wallet);
        setScoring(true);
        startPolling();
      } catch {
        // Could not score
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleRescore() {
    setScoring(true);
    try {
      // Remember current score ID so we can detect when a NEW one arrives
      scoreIdBeforePolling.current = score?.id || null;
      await requestScore(wallet);
      startPolling();
    } catch {
      setScoring(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl shimmer mx-auto" />
          <p className="text-slate-500 font-mono text-sm animate-pulse">
            Loading agent data...
          </p>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "transactions", label: "Transactions" },
    { id: "positions", label: "Positions" },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-display font-extrabold text-white">
            {agent?.agent_name || `Agent ${wallet.slice(0, 8)}...`}
          </h1>
          <p className="text-sm text-slate-500 font-mono">{wallet}</p>
          {agent?.ens_name && (
            <p className="text-sm text-accent font-mono">{agent.ens_name}</p>
          )}
        </div>
        <div className="flex gap-2 items-center">
          {agent?.platform && <PlatformBadge platform={agent.platform} />}
          <button
            onClick={handleRescore}
            disabled={scoring}
            className="px-4 py-2 bg-accent/15 hover:bg-accent/25 border border-accent/20 text-accent rounded-xl text-sm font-display font-bold tracking-wide transition-all disabled:opacity-40"
          >
            {scoring ? "SCORING..." : "RE-SCORE"}
          </button>
        </div>
      </div>

      {/* Scoring in progress */}
      {scoring && !score && (
        <div className="glass-card p-6 text-center border-accent/15">
          <div className="flex items-center justify-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <p className="text-accent/80 font-mono text-sm">
              Scoring in progress &mdash; analyzing onchain data across platforms...
            </p>
          </div>
        </div>
      )}

      {/* Score Card */}
      {score && (
        <ScoreCard
          score={score.score}
          tier={score.tier}
          collateral_requirement={score.collateral_requirement}
          max_loan_usdc={score.max_loan_usdc}
          rationale={score.rationale}
          key_factors={score.key_factors || []}
          risk_flags={score.risk_flags || []}
          ensip25_verified={score.ensip25_verified || false}
          ens_name={score.ens_name}
        />
      )}

      {/* Tab Bar */}
      <div className="flex gap-1 bg-surface-2/40 rounded-lg p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-xs font-mono px-4 py-2 rounded-md transition-all ${
              activeTab === tab.id
                ? "bg-accent/15 text-accent border border-accent/20"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <>
          {/* PnL Card */}
          {pnl && <PnLCard pnl={pnl} />}

          {/* Feature Radar + Score History */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features && <FeatureRadar features={features} />}
            <ScoreHistory scores={history} />
          </div>

          {/* Raw Features */}
          {features && (
            <div className="glass-card p-6">
              <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
                FEATURE VECTOR ({Object.keys(features).filter(
                  (k) =>
                    !["platforms_list", "id", "agent_id", "last_updated_at"].includes(k)
                ).length} SIGNALS)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(features)
                  .filter(
                    ([k]) =>
                      !["platforms_list", "id", "agent_id", "last_updated_at"].includes(k)
                  )
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="bg-surface-2/40 border border-surface-3/30 rounded-lg p-2.5"
                    >
                      <p className="text-[10px] text-slate-500 font-mono truncate">
                        {key}
                      </p>
                      <p className="text-sm font-mono font-medium text-slate-200 mt-0.5">
                        {String(value)}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === "transactions" && <TransactionTable wallet={wallet} />}

      {activeTab === "positions" && <PositionsList wallet={wallet} />}

      {/* No score CTA */}
      {!score && !scoring && (
        <div className="text-center py-16 space-y-4">
          <p className="text-slate-500 font-mono text-sm">
            No score found for this agent.
          </p>
          <button
            onClick={handleRescore}
            className="px-6 py-3 bg-accent/15 hover:bg-accent/25 border border-accent/20 text-accent rounded-xl font-display font-bold tracking-wide transition-all"
          >
            REQUEST SCORE
          </button>
        </div>
      )}
    </div>
  );
}
