
"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { getAgent, getScoreHistory, requestScore, getActivityHeatmap, getAgentAnalysis } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import ScoreCard from "@/components/ScoreCard";
import FeatureRadar from "@/components/FeatureRadar";
import ScoreHistory from "@/components/ScoreHistory";
import PlatformBadge from "@/components/PlatformBadge";
import TransactionTable from "@/components/TransactionTable";
import LenderPortal from "@/components/LenderPortal";
import AIAnalysis from "@/components/AIAnalysis";
import Tooltip from "@/components/Tooltip";
import TransactionCharts from "@/components/TransactionCharts";

type Tab = "overview" | "analysis" | "transactions";

const PIPELINE_STEPS = [
  "Initializing Agent Crawlers...",
  "Fetching On-Chain Data (Alchemy)...",
  "Verifying Identity (ENS & ERC-8004)...",
  "Aggregating Behavioral Features...",
  "Running ML Anomaly Detection...",
  "Calculating Final Credit Score..."
];

const SIGNAL_MAP: Record<string, { label: string; desc: string; icon?: string; category: string }> = {
  wallet_age_days: { label: "Wallet Age", desc: "Days since the first transaction on Base.", category: "Activity" },
  tx_count_total: { label: "Total Transactions", desc: "Lifetime transaction count for this agent.", category: "Activity" },
  tx_count_90d: { label: "Recent Activity (90D)", desc: "Activity in the last 3 months. Higher is better.", category: "Activity" },
  total_trades: { label: "Total Trades", desc: "Number of swap/trade transactions detected.", category: "Activity" },
  avg_trade_size_usd: { label: "Avg Trade Size", desc: "Average USD volume per trade operation.", category: "Economics" },
  tvl_usd: { label: "Net Asset Value (NAV)", desc: "Total Value Locked across all positions.", category: "Economics" },
  balance_eth: { label: "Native ETH", desc: "Current ETH liquidity held in wallet.", category: "Economics" },
  balance_usdc: { label: "USDC Liquidity", desc: "Stablecoin reserves for operations.", category: "Economics" },
  staking_balance_usd: { label: "Staked Assets", desc: "Capital currently locked in staking contracts.", category: "Economics" },
  total_pnl_usd: { label: "Total PnL", desc: "Estimated historical profit/loss performance.", category: "Economics" },
  win_rate: { label: "Trading Win %", desc: "Ratio of successful trades to total trades.", category: "Economics" },
  token_diversity: { label: "Asset Diversity", desc: "Number of unique tokens in portfolio.", category: "Economics" },
  defi_protocol_count: { label: "Protocol Reach", desc: "Number of unique DeFi protocols engaged.", category: "Activity" },
  nft_count: { label: "NFT Inventory", desc: "Count of unique digital assets/collectibles.", category: "Economics" },
  erc8004_reputation: { label: "ERC-8004 Rep", desc: "On-chain reputation score for AI agents.", category: "Reputation" },
  erc8004_job_count: { label: "Reputation Jobs", desc: "Completed jobs recorded via ERC-8004.", category: "Reputation" },
  ensip25_verified: { label: "Identity Verified", desc: "Self-sovereign identity linked via ENSIP-25.", category: "Reputation" },
  cross_chain_count: { label: "Chain Presence", desc: "Number of L2s/Chains active on.", category: "Activity" },
  platform_count: { label: "Platform Citations", desc: "Number of AI directories indexing this agent.", category: "Market" },
  virtuals_mcap_usd: { label: "Virtuals M-Cap", desc: "Valuation according to Virtuals.io market.", category: "Market" },
  virtuals_holder_count: { label: "Asset Holders", desc: "Number of unique token holders on Virtuals.", category: "Market" },
  olas_job_count: { label: "Olas Compute", desc: "Computational jobs completed on Olas stack.", category: "Reputation" },
  tee_secured: { label: "TEE Execution", desc: "Execution verified via Trusted Execution Environment.", category: "Reputation" },
  heyelsa_risk_score: { label: "Safety Rating", desc: "0-100 risk assessment (Lower is Safer).", category: "Safety" },
  heyelsa_wallet_label: { label: "Behavioral Tag", desc: "AI classification of wallet behavior.", category: "Market" },
};

export default function AgentPage() {
  const params = useParams();
  const wallet = params.wallet as string;

  const [agent, setAgent] = useState<any>(null);
  const [score, setScore] = useState<any>(null);
  const [features, setFeatures] = useState<any>(null);
  const [activityData, setActivityData] = useState<any[]>([]);
  const [agentAnalysis, setAgentAnalysis] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!scoring) {
      setStepIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev < PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
    }, 2500);
    return () => clearInterval(interval);
  }, [scoring]);

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
          setScoring(false);

          // Refresh others
          const [hist, activity, analysis] = await Promise.all([
            getScoreHistory(wallet).catch(() => ({ scores: [] })),
            getActivityHeatmap(wallet).catch(() => ({ activity: [] })),
            getAgentAnalysis(wallet).catch(() => ({ analysis: null }))
          ]);
          setHistory(hist.scores || []);
          setActivityData(activity.activity || []);
          setAgentAnalysis(analysis.analysis);
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
      }
      setHistory(historyData.scores || []);

      // Fetch overview + analysis data
      const [activity, analysis] = await Promise.all([
        getActivityHeatmap(wallet).catch(() => ({ activity: [] })),
        getAgentAnalysis(wallet).catch(() => ({ analysis: null }))
      ]);
      setActivityData(activity.activity || []);
      setAgentAnalysis(analysis.analysis);

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
            {[0, 1, 2].map(i => (
              <div key={i} className="w-2 h-8 bg-[#1DB954] rounded-full animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
          <p className="text-gray-400 font-mono text-sm">Loading agent data...</p>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "❖" },
    { id: "analysis", label: "Analysis", icon: "✧" },
    { id: "transactions", label: "Transactions", icon: "⇄" },
  ];

  const categories = ["Activity", "Economics", "Reputation", "Safety", "Market"];

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
        <div className="glass-card p-12 text-center border-[#1DB954]/20 flex flex-col items-center justify-center min-h-[300px]">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            className="w-8 h-8 rounded-full border-t-2 border-b-2 border-[#1DB954] mb-6"
          />
          <div className="h-6 relative w-full max-w-md overflow-hidden flex justify-center">
            <AnimatePresence mode="popLayout">
              <motion.h3
                key={PIPELINE_STEPS[stepIndex]}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -20, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="text-lg font-display font-black text-gray-900 absolute"
              >
                {PIPELINE_STEPS[stepIndex]}
              </motion.h3>
            </AnimatePresence>
          </div>
          <p className="text-sm text-gray-500 font-mono mt-4 max-w-md mx-auto">
            Deep ML behavioral analysis is running. This usually takes 15-30 seconds.
          </p>
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
            className={`flex items-center gap-1.5 text-sm font-display font-semibold px-5 py-2 rounded-lg transition-all ${activeTab === tab.id
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

          <TransactionCharts wallet={wallet} />

          <div className={`grid grid-cols-1 ${features && history.length > 0 ? 'md:grid-cols-2' : 'md:grid-cols-1'} gap-6`}>
            {features && <FeatureRadar features={features} />}
            {history.length > 0 && <ScoreHistory scores={history} />}
          </div>

          {score && <LenderPortal wallet={wallet} score={score} />}

          {/* Feature Vector Grouped */}
          {features && (
            <div className="glass-card p-8 space-y-10">
              <div className="flex items-center justify-between">
                <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">
                  Agent Metadata & Feature Signals
                </h3>
                <span className="text-[10px] text-[#1DB954] font-mono font-bold bg-[#1DB954]/10 px-2 py-1 rounded">
                  {Object.keys(features).length} RAW INPUTS
                </span>
              </div>

              <div className="space-y-8">
                {categories.map((cat) => {
                  const catSignals = Object.entries(features).filter(([key]) => SIGNAL_MAP[key]?.category === cat);
                  if (catSignals.length === 0) return null;

                  return (
                    <div key={cat} className="space-y-4">
                      <h4 className="text-xs font-display font-bold text-gray-900 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                        {cat}
                      </h4>
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                        {catSignals.map(([key, value]) => {
                          const meta = SIGNAL_MAP[key];
                          const displayVal = value === null ? "null" : String(value);

                          return (
                            <div
                              key={key}
                              className="bg-gray-50/50 border border-gray-100 hover:border-gray-300 rounded-xl p-4 transition-all group relative"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <p className="text-[10px] text-gray-500 font-display font-bold truncate">
                                  {meta?.label || key.replace(/_/g, " ").toUpperCase()}
                                </p>
                                <Tooltip content={meta?.desc || "Raw parameter from on-chain analysis."}>
                                  <div className="cursor-help text-gray-300 hover:text-gray-600">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>
                                  </div>
                                </Tooltip>
                              </div>

                              <p className={`text-sm font-mono font-bold ${displayVal === "true" ? "text-[#1DB954]" :
                                displayVal === "false" ? "text-[#FF3B30]" :
                                  displayVal === "null" || displayVal === "0" ? "text-gray-400" :
                                    "text-gray-900"
                                }`}>
                                {displayVal}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}                </div>
            </div>
          )}
        </>
      )}
      {activeTab === "analysis" && (
        <AIAnalysis
          analysis={agentAnalysis}
          activityData={activityData}
          features={features}
        />
      )}

      {activeTab === "transactions" && <TransactionTable wallet={wallet} />}

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
