"use client";

import { motion } from "framer-motion";

interface TransactionAnalysisProps {
  summary: string;
  patterns: string[];
  risk_indicators: string[];
  notable_transactions: string[];
  activity_profile: string;
}

const PROFILE_STYLES: Record<string, { label: string; color: string }> = {
  active_trader: { label: "Active Trader", color: "text-amber-400 bg-amber-500/10 border-amber-500/30" },
  defi_user: { label: "DeFi User", color: "text-blue-400 bg-blue-500/10 border-blue-500/30" },
  holder: { label: "HODLer", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
  nft_collector: { label: "NFT Collector", color: "text-purple-400 bg-purple-500/10 border-purple-500/30" },
  dormant: { label: "Dormant", color: "text-slate-400 bg-slate-500/10 border-slate-500/30" },
  mixed: { label: "Mixed Activity", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30" },
  unknown: { label: "Unknown", color: "text-slate-500 bg-slate-500/10 border-slate-500/30" },
};

export default function TransactionAnalysisCard({
  summary,
  patterns,
  risk_indicators,
  notable_transactions,
  activity_profile,
}: TransactionAnalysisProps) {
  const profile = PROFILE_STYLES[activity_profile] || PROFILE_STYLES.unknown;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-8 space-y-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase">
          AI TRANSACTION ANALYSIS
        </h3>
        <span className={`px-3 py-1 rounded-lg border text-xs font-medium ${profile.color}`}>
          {profile.label}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-slate-300 leading-relaxed">{summary}</p>

      {/* Patterns */}
      {patterns.length > 0 && (
        <div>
          <h4 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-2">
            BEHAVIORAL PATTERNS
          </h4>
          <div className="space-y-1.5">
            {patterns.map((p, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-xs text-slate-300"
              >
                <span className="text-accent mt-0.5 shrink-0">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </span>
                {p}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Indicators */}
      {risk_indicators.length > 0 && (
        <div>
          <h4 className="text-[10px] text-red-400/70 font-mono tracking-wider uppercase mb-2">
            RISK INDICATORS
          </h4>
          <div className="flex flex-wrap gap-2">
            {risk_indicators.map((r, i) => (
              <span
                key={i}
                className="px-3 py-1.5 bg-red-500/8 text-red-400/90 border border-red-500/15 rounded-lg text-xs font-medium"
              >
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Notable Transactions */}
      {notable_transactions.length > 0 && (
        <div>
          <h4 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-2">
            NOTABLE TRANSACTIONS
          </h4>
          <div className="space-y-1.5">
            {notable_transactions.map((t, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-xs text-slate-400"
              >
                <span className="text-slate-500 mt-0.5 shrink-0">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </span>
                {t}
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
