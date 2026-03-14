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
import LenderPortal from "@/components/LenderPortal";

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

  const scoreIdBeforePolling = useRef<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
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
        if (data?.latest_score && data.latest_score.id !== scoreIdBeforePolling.current) {
          stopPolling();
          setAgent(data.agent);
          setScore(data.latest_score);
          setFeatures(data.features);
          setPnl(data.pnl);
          setScoring(false);
          const hist = await getScoreHistory(wallet).catch(() => ({ scores: [] }));
          setHistory(hist.scores || []);
        }
      } catch {
        // keep polling
      }
    }, 3000);
  }, [wallet, stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [wallet, stopPolling]);

  useEffect(() => {
    loadData();

    const channel = supabase
      .channel(`score:${wallet}`)
      .on("postgres_changes", {
        event: "INSERT",
        schema: "public",
        table: "scores",
        filter: `wallet_address=eq.${wallet}`,
      }, (payload) => {
        stopPolling();
        setScore(payload.new);
        setScoring(false);
        loadData();
      })
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

      if (!agentData?.latest_score) {
        try {
          scoreIdBeforePolling.current = null;
          await requestScore(wallet);
          setScoring(true);
          startPolling();
        } catch (err) {
          console.error("[AgentPage] requestScore failed:", err);
        }
      }
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
        <div className="text-center space-y-4">
          <div className="flex gap-1 justify-center">
            {[0,1,2].map(i => (
              <div key={i} className="w-2 h-8 bg-[#1DB954] rounded-full animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
          <p className="text-gray-400 font-mono text-sm">Loading agent data...</p>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "transactions", label: "Transactions", icon: "🔁" },
    { id: "positions", label: "Positions", icon: "💼" },
  ];

  return (
    <div className="space-y-8 animate-fade-in">

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            {agent?.platform && <PlatformBadge platform={agent.platform} />}
            <h1 className="text-3xl font-display font-black text-gray-900 tracking-tight">
              {agent?.agent_name || `Agent ${wallet.slice(0, 8)}...`}
            </h1>
          </div>
          <p className="text-sm text-gray-400 font-mono break-all">{wallet}</p>
          {agent?.ens_name && (
            <p className="text-sm text-[#1DB954] font-mono">{agent.ens_name}</p>
          )}
        </div>

        {/* Rescore button */}
        <button
          onClick={handleRescore}
          disabled={scoring}
          className="flex-shrink-0 px-5 py-2.5 bg-[#1DB954]/10 hover:bg-[#1DB954]/20 border border-[#1DB954]/30 text-[#1DB954] rounded-xl text-sm font-display font-bold tracking-wide transition-all disabled:opacity-40"
        >
          {scoring ? "⏳ SCORING..." : "↺ RE-SCORE"}
        </button>
      </div>

      {/* ── Scoring in progress ── */}
      {scoring && !score && (
        <div className="glass-card p-6 border-[#1DB954]/20">
          <div className="flex items-center justify-center gap-3">
            <div className="flex gap-1">
              {[0,1,2].map(i => (
                <div key={i} className="w-1.5 h-4 bg-[#1DB954] rounded-full animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
            <p className="text-[#1DB954] font-mono text-sm">
              Scoring in progress — analyzing on-chain data across platforms...
            </p>
          </div>
        </div>
      )}

      {/* ── Score Card ── */}
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

      {/* ── Tab Bar ── */}
      <div className="flex gap-0 bg-gray-100 rounded-xl p-1 w-fit border border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 text-sm font-display font-semibold px-5 py-2 rounded-lg transition-all ${
              activeTab === tab.id
                ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ── */}
      {activeTab === "overview" && (
        <>
          {pnl && <PnLCard pnl={pnl} />}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features && <FeatureRadar features={features} />}
            <ScoreHistory scores={history} />
          </div>

          {score && <LenderPortal wallet={wallet} score={score} />}

          {/* Feature Vector */}
          {features && (
            <div className="glass-card p-6">
              <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-4">
                Feature Vector ({Object.keys(features).filter(
                  (k) => !["platforms_list", "id", "agent_id", "last_updated_at"].includes(k)
                ).length} Signals)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(features)
                  .filter(([k]) => !["platforms_list", "id", "agent_id", "last_updated_at"].includes(k))
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3"
                    >
                      <p className="text-[10px] text-gray-400 font-mono truncate">{key}</p>
                      <p className={`text-sm font-mono font-semibold mt-0.5 ${
                        String(value) === "true" ? "text-[#1DB954]" :
                        String(value) === "false" ? "text-[#FF3B30]" :
                        String(value) === "null" || String(value) === "0" ? "text-gray-400" :
                        "text-gray-900"
                      }`}>
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

      {/* ── No score CTA ── */}
      {!score && !scoring && (
        <div className="text-center py-16 glass-card space-y-4">
          <p className="text-5xl">📊</p>
          <p className="text-gray-500 font-body text-sm">No score found for this agent.</p>
          <button
            onClick={handleRescore}
            className="btn-primary"
          >
            Request Score
          </button>
        </div>
      )}
    </div>
  );
}
