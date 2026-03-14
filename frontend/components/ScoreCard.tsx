"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface ScoreCardProps {
  score: number;
  tier: string;
  collateral_requirement: number;
  max_loan_usdc: number;
  rationale: string;
  key_factors: string[];
  risk_flags: string[];
  ensip25_verified?: boolean;
  ens_name?: string | null;
}

const TIER_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  S: { color: "#1DB954", bg: "#1DB95412", border: "#1DB95430", label: "Excellent" },
  A: { color: "#5E5CE6", bg: "#5E5CE612", border: "#5E5CE630", label: "Very Good" },
  B: { color: "#007AFF", bg: "#007AFF12", border: "#007AFF30", label: "Good" },
  C: { color: "#FF9F0A", bg: "#FF9F0A12", border: "#FF9F0A30", label: "Fair" },
  D: { color: "#FF3B30", bg: "#FF3B3012", border: "#FF3B3030", label: "Poor" },
};

export default function ScoreCard({
  score,
  tier,
  collateral_requirement,
  max_loan_usdc,
  rationale,
  key_factors,
  risk_flags,
  ensip25_verified = false,
  ens_name,
}: ScoreCardProps) {
  const [displayScore, setDisplayScore] = useState(0);
  const tierCfg = TIER_CONFIG[tier] || TIER_CONFIG["D"];

  useEffect(() => {
    const duration = 1200;
    const steps = 60;
    const increment = score / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setDisplayScore(score);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [score]);

  const pct = Math.min(100, Math.round((score / 1000) * 100));

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="glass-card overflow-hidden"
    >
      {/* Tier color accent bar */}
      <div className="h-1.5" style={{ background: tierCfg.color }} />

      <div className="p-8 space-y-6">
        {/* Score + Tier row */}
        <div className="flex items-center gap-8">
          {/* Score number */}
          <div className="text-center">
            <p
              className="text-7xl font-display font-black leading-none"
              style={{ color: tierCfg.color }}
            >
              {displayScore}
            </p>
            <p className="text-xs text-gray-400 font-mono mt-1 tracking-widest">/ 1000</p>
          </div>

          <div className="h-16 w-px bg-gray-200" />

          {/* Tier badge + ENSIP */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-3">
              <span
                className="tier-badge text-base px-4 py-1.5"
                style={{ color: tierCfg.color, background: tierCfg.bg, borderColor: tierCfg.border }}
              >
                TIER {tier}
              </span>
              <span className="text-sm text-gray-400 font-body">{tierCfg.label}</span>
            </div>

            {/* ENSIP-25 badge */}
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium ${
                ensip25_verified
                  ? "bg-[#1DB954]/10 border-[#1DB954]/40 text-[#1DB954]"
                  : "bg-gray-100 border-gray-200 text-gray-400"
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                {ensip25_verified ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.5h.008v.008H12v-.008z" />
                )}
              </svg>
              ENSIP-25
              {ensip25_verified && ens_name && (
                <span className="font-mono text-xs opacity-80 ml-0.5">{ens_name}</span>
              )}
              {ensip25_verified && (
                <span className="text-[#1DB954] font-bold ml-0.5">+30pts</span>
              )}
            </div>
          </div>

          {/* Score progress arc — right side */}
          <div className="ml-auto flex-shrink-0 w-24">
            <div className="relative">
              <svg viewBox="0 0 100 60" className="w-full">
                {/* Track */}
                <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="#e0e0e0" strokeWidth="10" strokeLinecap="round" />
                {/* Fill */}
                <path
                  d="M 10 55 A 40 40 0 0 1 90 55"
                  fill="none"
                  stroke={tierCfg.color}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${pct * 1.26} 126`}
                />
              </svg>
              <p className="text-center text-xs font-mono text-gray-400 -mt-1">{pct}%</p>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[10px] font-mono text-gray-400">
            <span>0</span>
            <span>CREDIT SCORE</span>
            <span>1000</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000"
              style={{ width: `${pct}%`, background: tierCfg.color }}
            />
          </div>
        </div>

        {/* Collateral + Max Loan */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
            <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-2">Collateral Required</p>
            <p className="text-3xl font-display font-black text-gray-900">
              {collateral_requirement}
              <span className="text-base text-gray-400 font-body font-normal ml-1">%</span>
            </p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
            <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-2">Max Loan</p>
            <p className="text-3xl font-display font-black text-[#1DB954]">
              ${max_loan_usdc.toLocaleString()}
              <span className="text-base text-gray-400 font-body font-normal ml-1">USDC</span>
            </p>
          </div>
        </div>

        {/* Rationale */}
        <div className="bg-gray-50 border border-gray-100 rounded-xl p-4">
          <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-2">Rationale</h3>
          <p className="text-sm text-gray-600 leading-relaxed">{rationale}</p>
        </div>

        {/* Key Factors */}
        {key_factors.length > 0 && (
          <div>
            <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-3">Key Factors</h3>
            <div className="flex flex-wrap gap-2">
              {key_factors.map((f, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-[#1DB954]/08 text-[#1DB954] border border-[#1DB954]/20 rounded-lg text-xs font-medium"
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Risk Flags */}
        {risk_flags.length > 0 && (
          <div>
            <h3 className="text-[10px] text-[#FF3B30]/70 font-mono tracking-widest uppercase mb-3">⚠ Risk Flags</h3>
            <div className="flex flex-wrap gap-2">
              {risk_flags.map((f, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-[#FF3B30]/08 text-[#FF3B30] border border-[#FF3B30]/20 rounded-lg text-xs font-medium"
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
